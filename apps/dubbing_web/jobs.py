from concurrent.futures import ThreadPoolExecutor
import json
import shutil
from pathlib import Path
import sys
import threading
from uuid import uuid4

from .config import ROOT
from .domain import timing, voice_key, speech_text
from . import media


class Jobs:
    def __init__(self, store):
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dubbing")
        self.items = {}
        self.lock = threading.RLock()
        self.tts = None
        self.model_status = "Chưa tải"
        for path in sorted(store.root.glob("projects/*/renders/*/job.json"), key=lambda p: p.stat().st_mtime):
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                if saved["status"] in ("queued", "running"):
                    saved.update(status="cancelled", message="Tác vụ bị gián đoạn. Tạo lại để tiếp tục các câu còn thiếu.")
                    self.write_record(path, saved)
                saved["cancel"] = threading.Event()
                self.items[saved["id"]] = saved
            except (ValueError, KeyError, OSError):
                continue

    @staticmethod
    def write_record(path, record):
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    def persist(self, job):
        path = self.store.directory(job["project"]) / "renders" / job["id"] / "job.json"
        self.write_record(path, self.public(job))

    @staticmethod
    def check_cancel(job):
        if job["cancel"].is_set():
            raise media.Cancelled("Đã dừng. Các câu đã tạo được giữ để tiếp tục lần sau.")

    def load_model(self):
        if self.tts is None:
            self.model_status = "Đang tải model CPU…"
            try:
                sys.path.insert(0, str(ROOT / "src"))
                from vieneu import Vieneu
                self.tts = Vieneu(mode="v3turbo", device="cpu", backend="onnx", precision="fp32")
                self.model_status = "Sẵn sàng"
            except Exception as exc:
                self.model_status = f"Lỗi tải model: {exc}"
                raise
        return self.tts

    def submit(self, project, kind, cue_id=None, allow_overlap=False, overflow_policy=None):
        with self.lock:
            if any(j["project"] == project["id"] and j["status"] in ("queued", "running") for j in self.items.values()):
                raise ValueError("Dự án đang có tác vụ. Hãy dừng hoặc chờ hoàn tất.")
            if kind == "generate" and cue_id:
                previous = project["revision"]
                project = {**project, "revision": previous + 1}
                self.store.save(project, expected=previous)
            id = uuid4().hex
            item = {"id": id, "project": project["id"], "revision": project["revision"], "kind": kind,
                    "status": "queued", "done": 0, "total": 0, "message": "Đang chờ", "warnings": [], "cancel": threading.Event()}
            destination = self.store.directory(project["id"]) / "renders" / id
            destination.mkdir()
            item["overflow_policy"] = overflow_policy
            self.persist(item)
            self.items[id] = item
            self.pool.submit(self.execute, item, project, cue_id, allow_overlap, overflow_policy)
            return self.public(item)

    @staticmethod
    def public(item):
        return {k: v for k, v in item.items() if k != "cancel"}

    def execute(self, job, project, cue_id, allow_overlap, overflow_policy=None):
        import soundfile as sf
        job["status"] = "running"
        root = self.store.directory(project["id"])
        dest = root / "renders" / job["id"]
        self.persist(job)
        try:
            self.check_cancel(job)
            required = int(project["media"]["duration"] * 48000 * 4 * 3 + 512 * 1024**2)
            if shutil.disk_usage(root).free < required:
                raise ValueError("Không đủ dung lượng đĩa dự phòng để xử lý âm thanh. Hãy giải phóng dung lượng.")
            if job["kind"] == "proxy":
                job["message"] = "Tạo video xem trước H.264…"
                audio_map = ["-map", f"0:{project['audio_index']}"] if project["audio_index"] is not None else ["-an"]
                media.run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-i", root / project["video_file"],
                    "-map", f"0:{project['media']['video_index']}", *audio_map,
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", dest / "proxy.mp4"], job["cancel"])
                self.check_cancel(job)
                job.update(status="complete", video_file=project["video_file"], audio_index=project["audio_index"], file=f"renders/{job['id']}/proxy.mp4", message="Video xem trước đã sẵn sàng.")
                return
            if job["kind"] == "sample":
                job["message"] = "Tạo mẫu giọng " + project["voice"] + "…"
                sample_text = "Xin chào, đây là giọng đọc mẫu cho bản lồng tiếng của bạn."
                cache = self.store.root / "samples"
                cache.mkdir(exist_ok=True)
                cached = cache / (voice_key({"text": sample_text}, project) + ".wav")
                if not cached.exists():
                    wav = self.load_model().infer(sample_text, voice=project["voice"])
                    temporary = dest / "sample-temp.wav"
                    sf.write(temporary, wav, 48000)
                    temporary.replace(cached)
                shutil.copyfile(cached, dest / "sample.wav")
                self.check_cancel(job)
                job.update(status="complete", file=f"renders/{job['id']}/sample.wav", message="Mẫu giọng đã sẵn sàng.")
                return
            # Reuse only a completed mix for the same project revision and overflow decision.
            # Regenerating a cue increments revision, so cached mixes cannot hide new speech.
            policy = overflow_policy or ("keep" if allow_overlap else None)
            reusable = [j for j in self.items.values() if j["id"] != job["id"] and
                        j["project"] == project["id"] and j["revision"] == project["revision"] and
                        j["status"] == "complete" and j.get("preview") and j.get("overflow_policy") == policy]
            if job["kind"] in ("mp3", "mkv") and reusable:
                cached = reusable[-1]
                source_mix = root / cached["preview"]
                if source_mix.is_file():
                    mp3 = dest / "dubbed.mp3"
                    shutil.copyfile(source_mix, mp3)
                    if job["kind"] == "mkv":
                        media.mux_mkv(project, root, mp3, dest / "output.mkv", job["cancel"])
                    self.check_cancel(job)
                    if self.store.get(project["id"])["revision"] != project["revision"]:
                        raise ValueError("Dự án đã thay đổi khi xuất. Hãy xuất lại.")
                    job.update(status="complete", preview=f"renders/{job['id']}/dubbed.mp3",
                               file=f"renders/{job['id']}/" + ("output.mkv" if job["kind"] == "mkv" else "dubbed.mp3"),
                               warnings=cached["warnings"], skipped_cues=cached.get("skipped_cues", []),
                               message="Đã xuất xong — tái sử dụng bản phối hiện hành.", reused_mix=True)
                    return
            cues = sorted(project["cues"], key=lambda c: c["start"])
            selected = [c for c in cues if not cue_id or c["id"] == cue_id]
            if not selected:
                raise ValueError("Không có câu để xử lý.")
            job["total"] = len(selected)
            for cue in selected:
                if job["cancel"].is_set():
                    raise media.Cancelled("Đã dừng.")
                path = root / "clips" / (voice_key(cue, project) + ".wav")
                if not path.exists() or (cue_id and job["kind"] == "generate"):
                    job["message"] = "Tạo giọng: " + cue["text"][:90]
                    wav = self.load_model().infer(speech_text(cue, project), voice=cue.get("voice") or project["voice"])
                    if not len(wav):
                        raise ValueError("Model trả về âm thanh rỗng.")
                    temporary = dest / "generated.wav"
                    sf.write(temporary, wav, 48000)
                    temporary.replace(path)
                job["done"] += 1
                self.persist(job)
                self.check_cancel(job)
            if job["kind"] == "generate":
                job["message"] = "Đã tạo giọng."
            else:
                rendered = []
                for i, cue in enumerate(cues):
                    source = root / "clips" / (voice_key(cue, project) + ".wav")
                    duration = sf.info(source).duration
                    end = cues[i+1]["start"] if i+1 < len(cues) else project["media"]["duration"]
                    fit = timing(duration, cue["start"], end, cue.get("speed") or project["speed"], project["auto_fit"], project["fit_limit"])
                    if fit["overflow"] > 0.02:
                        job["warnings"].append({"cue": i+1, "seconds": round(fit["overflow"], 3)})
                        if overflow_policy == "skip":
                            job.setdefault("skipped_cues", []).append(i + 1)
                            continue
                    output = dest / f"cue-{i}.wav"
                    media.tempo(source, output, fit["speed"], job["cancel"])
                    info = sf.info(output)
                    rendered.append({"start": cue["start"], "duration": info.duration, "frames": info.frames, "path": output})
                if job["warnings"] and not allow_overlap and overflow_policy is None:
                    job["status"] = "needs_confirmation"
                    job["message"] = "Có câu tràn khung. Xem cảnh báo rồi chọn tiếp tục để giữ mốc và cho phép chồng lời."
                    return
                job["message"] = "Đang trộn âm thanh…"
                wav = dest / "mix.wav"
                mp3 = dest / "dubbed.mp3"
                media.mix(project, root, rendered, wav, job["cancel"])
                media.encode_mp3(wav, mp3, job["cancel"])
                if job["kind"] == "mkv":
                    job["message"] = "Đang ghép MKV hai track…"
                    media.mux_mkv(project, root, mp3, dest / "output.mkv", job["cancel"])
                current = self.store.get(project["id"])
                if current["revision"] != project["revision"]:
                    raise ValueError("Dự án đã thay đổi khi xuất. Hãy xuất lại phiên bản mới nhất.")
                job["file"] = f"renders/{job['id']}/" + ("output.mkv" if job["kind"] == "mkv" else "dubbed.mp3")
                job["preview"] = f"renders/{job['id']}/dubbed.mp3"
                skipped = job.get("skipped_cues", [])
                job["message"] = f"Đã xuất xong. Bỏ qua {len(skipped)} câu tràn: " + ", ".join(map(str, skipped)) if skipped else "Đã xuất xong."
            self.check_cancel(job)
            job["status"] = "complete"
        except media.Cancelled as exc:
            job.update(status="cancelled", message=str(exc))
        except Exception as exc:
            job.update(status="error", message=str(exc))
        finally:
            self.persist(job)
            keep = {"job.json"}
            if job["status"] == "complete":
                keep.update(Path(job[key]).name for key in ("file", "preview") if job.get(key))
            for path in dest.iterdir():
                if path.is_file() and path.name not in keep:
                    try:
                        path.unlink()
                    except OSError:
                        pass  # A player may still hold a file on Windows; retry on later cleanup.

    def shutdown(self):
        for job in self.items.values():
            job["cancel"].set()
        self.pool.shutdown(wait=False, cancel_futures=True)
