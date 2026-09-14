"""Media operations shared by Windows and Linux. No shell command strings."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .config import executable


class Cancelled(RuntimeError):
    pass


def run(name, arguments, cancel=None):
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen([executable(name), *map(str, arguments)], stdout=output,
                                   stderr=subprocess.STDOUT, creationflags=flags)
        while process.poll() is None:
            if cancel and cancel.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise Cancelled("Đã dừng tác vụ.")
            time.sleep(0.1)
        output.seek(0)
        result = output.read().decode("utf-8", errors="replace")
        allowed = (0, 1) if name == "mkvmerge" else (0,)
        if process.returncode not in allowed:
            raise RuntimeError(f"{name}: {result[-3000:]}")
        return result


def probe(path):
    return json.loads(run("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", path]))


def identify(path):
    return json.loads(run("mkvmerge", ["-J", path]))


def inspect_video(path):
    info = probe(path)
    videos = [s for s in info["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    if not videos:
        raise ValueError("File không có luồng video.")
    video_start = float(videos[0].get("start_time", 0))
    container = info.get("format", {}).get("format_name", "")
    if videos[0].get("duration") is not None:
        duration = float(videos[0]["duration"])
    else:
        duration = float(info.get("format", {}).get("duration", 0))
        if "matroska" in container:
            duration -= max(0, video_start)
    if duration <= 0 or duration > 24 * 3600:
        raise ValueError("Video phải có thời lượng hợp lệ, tối đa 24 giờ.")
    audios = [{"index": s["index"], "codec": s["codec_name"], "channels": s.get("channels"),
               "language": s.get("tags", {}).get("language", "und"),
               "title": s.get("tags", {}).get("title", f"Audio {i + 1}"),
               "default": bool(s.get("disposition", {}).get("default")),
               "start": float(s.get("start_time", 0))} for i, s in enumerate(info["streams"]) if s["codec_type"] == "audio"]
    return {"duration": duration, "video_index": videos[0]["index"],
            "video_start": float(videos[0].get("start_time", 0)), "audio_tracks": audios,
            "container": info["format"].get("format_name", "")}


def tempo(source, destination, speed, cancel):
    # Keep every atempo stage <= 2 to avoid sample skipping at high speeds.
    factors = []
    while speed > 2:
        factors.append(2)
        speed /= 2
    factors.append(speed)
    run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-i", source, "-af",
                    ",".join(f"atempo={n:.8f}" for n in factors), "-ar", "48000", "-ac", "1", destination], cancel)


def mix(project, directory, rendered, destination, cancel):
    """Write PCM in blocks; overlapping voice clips add rather than overwrite."""
    import numpy as np
    import soundfile as sf

    duration = max(project["media"]["duration"], max((c["start"] + c["duration"] for c in rendered), default=0))
    total = int(round(duration * 48000))
    background = destination.parent / "background.wav"
    source = directory / project["video_file"]
    if project["audio_index"] is not None and project["background"] != "off":
        # Decode selected source including its relative start offset on the video timeline.
        audio = next(a for a in project["media"]["audio_tracks"] if a["index"] == project["audio_index"])
        offset = audio["start"] - project["media"].get("video_start", 0)
        sync = f"adelay={round(offset*1000)}:all=1" if offset >= 0 else f"atrim=start={-offset},asetpts=PTS-STARTPTS"
        run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-i", source, "-map", f"0:{project['audio_index']}",
                       "-vn", "-af", sync, "-ac", "2", "-ar", "48000", "-c:a", "pcm_f32le", background], cancel)
    base_gain, speaking_gain = {"duck": (0.3, 0.10), "original_duck": (1, 0.22), "original": (1, 1), "quiet": (0.06, 0.06), "off": (0, 0)}[project["background"]]
    # Gain choices are project defaults, not claimed to reproduce proprietary mixing.
    intervals = sorted((max(0, c["start"]), c["start"] + c["duration"]) for c in rendered)
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    bg = sf.SoundFile(background) if background.exists() else None
    try:
        with sf.SoundFile(destination, "w", samplerate=48000, channels=2, subtype="FLOAT") as output:
            for at in range(0, total, 48000):
                if cancel.is_set():
                    raise Cancelled("Đã dừng.")
                count = min(48000, total - at)
                block = np.zeros((count, 2), dtype=np.float32)
                if bg:
                    values = bg.read(count, dtype="float32", always_2d=True)
                    block[:len(values)] = values
                t = (np.arange(count) + at) / 48000
                envelope = np.zeros(count)
                for start, end in merged:
                    if end + 0.25 < t[0] or start - 0.08 > t[-1]:
                        continue
                    env = np.minimum(np.clip((t - start + 0.08) / 0.08, 0, 1), np.clip((end + 0.25 - t) / 0.25, 0, 1))
                    envelope = np.maximum(envelope, env)
                block *= (base_gain + (speaking_gain - base_gain) * envelope)[:, None]
                for cue in rendered:
                    start = round(cue["start"] * 48000)
                    length = cue["frames"]
                    left, right = max(at, start), min(at + count, start + length)
                    if right > left:
                        with sf.SoundFile(cue["path"]) as wav:
                            wav.seek(left - start)
                            clip = wav.read(right - left, dtype="float32", always_2d=True)
                        block[left-at:right-at] += clip
                output.write(block)
    finally:
        if bg:
            bg.close()
        background.unlink(missing_ok=True)


def encode_mp3(wav, destination, cancel):
    run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-i", wav, "-af", "alimiter=limit=0.95:level=false:latency=true",
                   "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k", destination], cancel)


def mux_mkv(project, directory, dubbed, destination, cancel):
    if project["audio_index"] is None:
        raise ValueError("Video không có âm gốc nên không thể xuất MKV đúng hai track. Bạn vẫn có thể tải MP3.")
    source = directory / project["video_file"]
    original_source = source
    try:
        info = identify(source)
        if not info.get("tracks"):
            raise RuntimeError("Không nhận diện được tracks.")
    except RuntimeError:
        source = destination.parent / "compatible-source.mkv"
        run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-i", original_source,
                       "-map", f"0:{project['media']['video_index']}", "-map", "0:a?", "-c", "copy", source], cancel)
        info = identify(source)
    tracks = info.get("tracks", [])
    video = next((t["id"] for t in tracks if t["type"] == "video"), None)
    audios = [t for t in tracks if t["type"] == "audio"]
    source_audios = project["media"]["audio_tracks"]
    ordinal = next(i for i, a in enumerate(source_audios) if a["index"] == project["audio_index"])
    if video is None or ordinal >= len(audios):
        raise ValueError("MKVToolNix không nhận diện được video/audio đã chọn.")
    original_id = audios[ordinal]["id"]
    dub_id = next(t["id"] for t in identify(dubbed)["tracks"] if t["type"] == "audio")
    args = ["-o", destination]
    if "matroska" in project["media"]["container"]:
        origin_shift = -round(project["media"].get("video_start", 0) * 1000)
        args += ["--track-order", f"0:{video},0:{original_id},1:{dub_id}", "--video-tracks", str(video),
                 "--audio-tracks", str(original_id), "--no-subtitles", "--no-attachments",
                 "--track-name", f"{original_id}:Original", "--default-track-flag", f"{original_id}:no",
                 "--forced-display-flag", f"{original_id}:no", "--sync", f"{video}:{origin_shift}", "--sync", f"{original_id}:{origin_shift}", source]
    else:
        original = destination.parent / "original.mka"
        run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-i", original_source, "-map", f"0:{project['audio_index']}",
                       "-vn", "-sn", "-dn", "-c:a", "copy", original], cancel)
        oid = next(t["id"] for t in identify(original)["tracks"] if t["type"] == "audio")
        extracted = probe(original)["streams"][0]
        selected = source_audios[ordinal]
        correction = round((selected["start"] - project["media"].get("video_start", 0) - float(extracted.get("start_time", 0))) * 1000)
        args += ["--track-order", f"0:{video},1:{oid},2:{dub_id}", "--video-tracks", str(video), "--no-audio",
                 "--no-subtitles", "--no-attachments", source, "--no-video", "--no-subtitles", "--no-chapters",
                 "--no-global-tags", "--audio-tracks", str(oid), "--sync", f"{oid}:{correction}",
                 "--track-name", f"{oid}:Original", "--default-track-flag", f"{oid}:no", original]
    args += ["--no-video", "--no-subtitles", "--no-chapters", "--no-global-tags", "--audio-tracks", str(dub_id),
             "--track-name", f"{dub_id}:Vietnamese Dub", "--language", f"{dub_id}:vi",
             "--default-track-flag", f"{dub_id}:yes", dubbed]
    log = run("mkvmerge", args, cancel)
    result = identify(destination)
    if sum(t["type"] == "audio" for t in result.get("tracks", [])) != 2:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Kết quả không có đúng hai audio track.")
    return log
