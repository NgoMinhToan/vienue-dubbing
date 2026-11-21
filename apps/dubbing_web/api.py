from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal

from .config import ROOT, Settings, executable
from .domain import Edit, SourceMissing, parse_srt, voice_key, timing, cue_warnings
from .store import Store, Conflict
from .jobs import Jobs
from .media import inspect_video
from .library import install_library
from .pronunciation import install_dictionary
from .media_browser import VIDEO_EXTENSIONS, install_media_browser, resolve_media
from .queueing import install_queue
from .studio import install_studio

SRT_LIMIT = 10 * 1024 * 1024
MEDIA_SUFFIXES = (".mp3", ".mkv", ".mp4", ".mov", ".avi", ".webm", ".m4v", ".wav")


class JobRequest(BaseModel):
    kind: Literal["generate", "mp3", "mkv", "proxy", "sample"] = "generate"
    cue_id: str | None = None
    allow_overlap: bool = False
    overflow_policy: Literal["keep", "skip"] | None = None


class SourcePathRequest(BaseModel):
    revision: int
    video: str


def create_app(settings=None):
    settings = settings or Settings.from_env()
    store = Store(settings.data)
    jobs = Jobs(store)
    presets = json.loads((ROOT / "src/vieneu/assets/voices_v3_turbo.json").read_text(encoding="utf-8"))
    voices = presets["presets"]

    def copy_upload(source, target):
        # No size cap: a video of any length is accepted as long as the disk can hold it.
        reserve = int(os.environ.get("APP_MIN_FREE_BYTES", 512 * 1024**2))
        while chunk := source.read(1024 * 1024):
            if shutil.disk_usage(settings.data).free < len(chunk) + reserve:
                raise ValueError("Không đủ dung lượng đĩa để lưu video. Hãy giải phóng dung lượng.")
            target.write(chunk)

    @asynccontextmanager
    async def lifespan(app):
        yield
        for state in app.state.studio_states.values():
            state["cancel"].set()
        jobs.shutdown()

    app = FastAPI(title="VieNeu Dubbing", lifespan=lifespan)
    app.state.store, app.state.jobs = store, jobs
    get_dictionary = install_dictionary(app, store, jobs)
    install_library(app, store, jobs, presets["presets"], get_dictionary)
    install_studio(app, store, jobs, presets["presets"], get_dictionary)
    queue = install_queue(app, store, jobs)

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        allowed = {"localhost", "127.0.0.1", "testserver"}
        if settings.host not in ("0.0.0.0", "::") and host not in allowed:
            return JSONResponse({"detail": "Host không hợp lệ."}, 403)
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Origin không hợp lệ."}, 403)
        return await call_next(request)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Không tìm thấy dự án hoặc tài nguyên."}, 404)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, 409)

    @app.exception_handler(SourceMissing)
    async def missing_source(request, exc):
        return JSONResponse({"detail": str(exc), "code": "source_missing"}, 409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, 400)

    @app.exception_handler(RuntimeError)
    async def failure(request, exc):
        return JSONResponse({"detail": str(exc)}, 503)

    def describe(project):
        import soundfile as sf
        root = store.directory(project["id"])
        proxies = [j for j in jobs.items.values() if j["project"] == project["id"] and j["kind"] == "proxy" and j["status"] == "complete" and j.get("video_file") == project["video_file"] and j.get("audio_index") == project["audio_index"]]
        project["proxy_file"] = proxies[-1]["file"] if proxies else None
        project["cue_warnings"] = cue_warnings(project["cues"], project["media"]["duration"])
        cues = sorted(project["cues"], key=lambda c: c["start"])
        for i, cue in enumerate(cues):
            key = voice_key(cue, project)
            path = root / "clips" / (key + ".wav")
            cue["ready"] = path.exists()
            if path.exists():
                end = cues[i+1]["start"] if i+1 < len(cues) else project["media"]["duration"]
                cue["fit"] = timing(sf.info(path).duration, cue["start"], end, cue.get("speed") or project["speed"], project["auto_fit"], project["fit_limit"])
                cue["audio"] = "clips/" + key + ".wav"
        return project

    def ensure_source(project):
        """Validate an in-place source and re-inspect it when the file changed.

        Raises SourceMissing when the project can no longer be opened safely.
        Returns a warning message when the video was re-analysed.
        """
        if not project.get("video_external"):
            return None
        path = Path(project.get("video_path") or "")
        try:
            stat = path.stat()
        except OSError as exc:
            raise SourceMissing(f"Không tìm thấy video nguồn {path.name or ''}. Chọn lại nguồn cho dự án trước khi mở.") from exc
        if not path.is_file():
            raise SourceMissing(f"Không tìm thấy video nguồn {path.name}. Chọn lại nguồn cho dự án trước khi mở.")
        previous = project.get("video_stat") or {}
        if previous.get("size") == stat.st_size and previous.get("mtime_ns") == stat.st_mtime_ns:
            return None
        try:
            info = inspect_video(path)
        except Exception as exc:
            raise SourceMissing(f"Video nguồn {path.name} đã thay đổi nhưng không đọc được. Chọn lại nguồn cho dự án.") from exc
        indices = [a["index"] for a in info["audio_tracks"]]
        if project.get("audio_index") not in indices:
            selected = next((a["index"] for a in info["audio_tracks"] if a["default"]), indices[0] if indices else None)
            project["audio_index"] = selected
        project["media"] = info
        project["video_stat"] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        store.save(project)
        return "Video nguồn đã thay đổi kể từ lúc nhập. Đã phân tích lại video; hãy kiểm tra lại phụ đề."

    @app.get("/api/health")
    def health():
        tools = {}
        for name in ("ffmpeg", "ffprobe", "mkvmerge"):
            try:
                tools[name] = executable(name)
            except RuntimeError:
                tools[name] = None
        return {"status": "ok", "model": jobs.model_status, "tools": tools, "backend": "CPU · v3 Turbo fp32"}

    @app.get("/api/voices")
    def get_voices():
        return [{"id": v, "description": value.get("description", "")} for v, value in list(voices.items())]

    @app.get("/api/projects")
    def projects():
        with jobs.lock:
            items = []
            for p in store.list():
                available = True
                if p.get("video_external"):
                    try:
                        available = Path(p.get("video_path") or "").is_file()
                    except OSError:
                        available = False
                items.append({"id": p["id"], "name": p["name"], "count": len(p["cues"]), "updated": p["updated"],
                              "revision": p["revision"], "video_name": p["video_name"], "available": available,
                              "queue":queue.summary(p['id'])})
            return items

    def read_srt(upload):
        raw = upload.file.read(SRT_LIMIT + 1)
        if len(raw) > SRT_LIMIT:
            raise ValueError("SRT quá lớn (tối đa 10 MB).")
        return parse_srt(raw)

    def video_suffix(name):
        suffix = Path(name or "").suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            raise ValueError("Định dạng video chưa hỗ trợ.")
        return suffix

    def project_record(name, id, video_path, video_name, cues, external):
        info = inspect_video(video_path)
        selected = next((a for a in info["audio_tracks"] if a["default"]), next(iter(info["audio_tracks"]), None))
        stat = video_path.stat()
        return {"id": id, "revision": 1, "name": name, "voice": "Kim Thanh" if "Kim Thanh" in voices else next(iter(voices)),
                "speed": 1, "auto_fit": True, "fit_limit": 1.6, "background": "duck",
                "audio_index": selected["index"] if selected else None,
                "video_name": Path(video_name).name, "video_file": video_path.name,
                "video_external": external,
                "video_path": str(video_path.resolve()) if external else None,
                "video_stat": {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns} if external else None,
                "media": info, "cues": cues, "pronunciation": get_dictionary()}

    @app.post("/api/projects")
    def create(name: str = Form("Lồng tiếng mới"), video: UploadFile = File(...), srt: UploadFile = File(...)):
        if not name.strip() or len(name) > 200:
            raise ValueError("Tên dự án không hợp lệ.")
        cues = read_srt(srt)
        suffix = video_suffix(video.filename)
        id, root = store.create()
        try:
            path = root / ("source" + suffix)
            with path.open("wb") as target:
                copy_upload(video.file, target)
            return describe(store.save(project_record(name, id, path, video.filename, cues, False)))
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

    def create_in_place(name, video, raw_srt):
        """Create a project whose video stays in APP_MEDIA_ROOT; only clips/renders are local."""
        if not name.strip() or len(name) > 200:
            raise ValueError("Tên dự án không hợp lệ.")
        if len(raw_srt) > SRT_LIMIT:
            raise ValueError("SRT quá lớn (tối đa 10 MB).")
        cues = parse_srt(raw_srt)
        video_suffix(video.name)
        id, root = store.create()
        try:
            return describe(store.save(project_record(name, id, video, video.name, cues, True)))
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

    install_media_browser(app, create, create_in_place)

    @app.get("/api/projects/{id}")
    def get(id: str):
        project = store.get(id)
        warning = ensure_source(project)
        project = describe(project)
        project["source_warning"] = warning
        saved = [j for j in jobs.items.values() if j["project"] == id and j["revision"] == project["revision"]]
        project["last_job"] = jobs.public(saved[-1]) if saved else None
        return project

    @app.put("/api/projects/{id}")
    def edit(id: str, values: Edit):
        with jobs.lock, store.lock:
            p = store.get(id)
            if values.voice not in voices or any(c.voice and c.voice not in voices for c in values.cues):
                raise ValueError("Giọng không hợp lệ.")
            if values.audio_index not in [a["index"] for a in p["media"]["audio_tracks"]] + ([None] if not p["media"]["audio_tracks"] else []):
                raise ValueError("Track âm gốc không hợp lệ.")
            if len({c.id for c in values.cues}) != len(values.cues):
                raise ValueError("ID câu bị trùng.")
            original = {c["id"]: c.get("original_text", c["text"]) for c in p["cues"]}
            edits = values.model_dump()
            for cue in edits["cues"]:
                cue["original_text"] = original.get(cue["id"], cue["text"])
            p.update(edits)
            p["revision"] += 1
            return describe(store.save(p, expected=values.revision))

    @app.post("/api/projects/{id}/source")
    def replace_source(id: str, revision: int = Form(...), video: UploadFile | None = File(None), srt: UploadFile | None = File(None)):
        with jobs.lock:
            p = store.get(id)
            if p["revision"] != revision:
                raise Conflict("Dự án đã thay đổi. Mở lại trước khi thay nguồn.")
            if any(j["project"] == id and j["status"] in ("queued", "running") for j in jobs.items.values()):
                raise ValueError("Dừng tác vụ trước khi thay nguồn.")
            if not video and not srt:
                raise ValueError("Chọn video hoặc SRT mới.")
            new_path = None
            try:
                if srt:
                    raw = srt.file.read(SRT_LIMIT + 1)
                    if len(raw) > SRT_LIMIT:
                        raise ValueError("SRT tối đa 10 MB.")
                    p["cues"] = parse_srt(raw)
                if video:
                    suffix = video_suffix(video.filename)
                    new_path = store.directory(id) / ("source-" + uuid4().hex + suffix)
                    with new_path.open("wb") as target:
                        copy_upload(video.file, target)
                    info = inspect_video(new_path)
                    selected = next((a for a in info["audio_tracks"] if a["default"]), next(iter(info["audio_tracks"]), None))
                    p.update(video_file=new_path.name, video_name=Path(video.filename).name, media=info,
                             audio_index=selected["index"] if selected else None,
                             video_external=False, video_path=None, video_stat=None)
                p["revision"] += 1
                return describe(store.save(p, expected=revision))
            except Exception:
                if new_path:
                    new_path.unlink(missing_ok=True)
                raise

    @app.post("/api/projects/{id}/source/in-place")
    def replace_source_in_place(id: str, values: SourcePathRequest):
        video = resolve_media(values.video)
        if not video.is_file() or video.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError("Cần chọn video hợp lệ trong thư mục nguồn.")
        with jobs.lock:
            p = store.get(id)
            if p["revision"] != values.revision:
                raise Conflict("Dự án đã thay đổi. Mở lại trước khi thay nguồn.")
            if any(j["project"] == id and j["status"] in ("queued", "running") for j in jobs.items.values()):
                raise ValueError("Dừng tác vụ trước khi thay nguồn.")
            info = inspect_video(video)
            selected = next((a for a in info["audio_tracks"] if a["default"]), next(iter(info["audio_tracks"]), None))
            stat = video.stat()
            p.update(video_file=video.name, video_name=video.name, media=info,
                     audio_index=selected["index"] if selected else None,
                     video_external=True, video_path=str(video),
                     video_stat={"size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
            p["revision"] += 1
            return describe(store.save(p, expected=values.revision))

    @app.delete("/api/projects/{id}")
    def delete(id: str, confirm_queue: bool=False):
        with jobs.lock:
            store.get(id)
            pending=any(j['project']==id and (j['status'] in ('waiting','queued','running') or j.get('_executing')) for j in jobs.items.values())
            if pending and not confirm_queue:
                raise Conflict('Dự án còn tác vụ/hàng đợi. Xác nhận hủy tất cả trước khi xóa.')
            if pending and queue.cancel_project(id):
                return JSONResponse({'pending':True,'message':'Đang dừng worker trước khi xóa.'},202)
            store.delete(id)
            shutil.rmtree(store.directory(id))
            for jid in [jid for jid,j in jobs.items.items() if j['project']==id]:
                jobs.items.pop(jid)
            return {"ok": True}

    @app.post("/api/projects/{id}/cleanup")
    def cleanup(id: str, confirm: bool = False):
        if not confirm:
            raise ValueError("Cần xác nhận dọn bản xuất/cache cũ.")
        with jobs.lock:
            p = store.get(id)
            if any(j["project"] == id and (j["status"] in ("queued", "running") or j.get('_executing')) for j in jobs.items.values()):
                raise ValueError("Đợi hoặc dừng tác vụ trước khi dọn dữ liệu.")
            root = store.directory(id).resolve()
            removed = 0
            # Keep current-revision outputs and a proxy matching the selected source track.
            for jid, record in list(jobs.items.items()):
                if record["project"] != id:
                    continue
                current = record["revision"] == p["revision"] and record["status"] == "complete"
                proxy = record["kind"] == "proxy" and record["status"] == "complete" and record.get("video_file") == p["video_file"] and record.get("audio_index") == p["audio_index"]
                if current or proxy or record.get('version'):
                    continue
                folder = (root / "renders" / jid).resolve()
                if folder.parent != root / "renders":
                    continue
                if folder.is_dir():
                    removed += sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                    shutil.rmtree(folder)
                jobs.items.pop(jid, None)
            keys = {voice_key(c, p) + ".wav" for c in p["cues"]}
            for record in jobs.items.values():
                if record['project']==id and record.get('version'):
                    snapshot=json.loads(queue.snapshot_path(record).read_text(encoding='utf-8'))
                    keys.update(voice_key(c,snapshot)+'.wav' for c in snapshot['cues'])
            for clip in (root / "clips").glob("*.wav"):
                if clip.name not in keys:
                    removed += clip.stat().st_size
                    clip.unlink()
            return {"removed_bytes": removed}

    @app.post("/api/projects/{id}/jobs")
    def submit(id: str, request: JobRequest):
        p = store.get(id)
        ensure_source(p)
        if request.cue_id and not any(c["id"] == request.cue_id for c in p["cues"]):
            raise ValueError("Câu không tồn tại.")
        if request.kind != "generate" and request.cue_id:
            raise ValueError("Xuất bản cần toàn bộ dự án.")
        if request.kind == "mkv" and p["audio_index"] is None:
            raise ValueError("Video không có âm gốc. Chọn xuất MP3.")
        return jobs.submit(p, request.kind, request.cue_id, request.allow_overlap, request.overflow_policy)

    @app.get("/api/jobs/{id}")
    def job(id: str):
        return jobs.public(jobs.items[id])

    @app.post("/api/jobs/{id}/cancel")
    def cancel(id: str):
        with jobs.lock:
            item=jobs.items[id]
            item["cancel"].set()
            if item['status'] in ('waiting','queued'):
                item.update(status='cancelled',message='Đã hủy tác vụ đang chờ.')
                jobs.persist(item)
        return {"ok": True}

    def output_root():
        return Path(settings.output or os.environ.get("APP_OUTPUT_DIR", "/app/output")).resolve()

    def safe_stem(name):
        stem = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", name)
        stem = re.sub(r"\s+", " ", stem).strip(" .")
        return stem[:120] or "du-an"

    @app.post("/api/jobs/{id}/save")
    def save_output(id: str):
        """Copy a completed MP3/MKV export into APP_OUTPUT_DIR without overwriting files."""
        item = jobs.items[id]
        if item.get("status") != "complete" or item.get("kind") not in ("mp3", "mkv") or not item.get("file"):
            raise ValueError("Chỉ lưu được bản xuất MP3/MKV đã hoàn tất.")
        project = store.get(item["project"])
        root = store.directory(item["project"]).resolve()
        source = (root / item["file"]).resolve()
        if not source.is_relative_to(root / "renders") or not source.is_file():
            raise HTTPException(409, "Bản xuất không còn trên máy. Hãy xuất lại.")
        if not item.get("version") and item["revision"] != project["revision"]:
            raise ValueError("Bản xuất không còn khớp với dự án. Hãy xuất lại.")
        destination = output_root()
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"Không tạo được thư mục lưu {destination}. Kiểm tra quyền ghi hoặc APP_OUTPUT_DIR.") from exc
        stem = safe_stem(project["name"])
        suffix = ".mkv" if item["kind"] == "mkv" else ".mp3"
        base = f"{stem}-v{item['version']}" if item.get("version") else f"{stem}-{item['id'][:6]}"
        for number in range(1, 10000):
            name = base + (f"-{number}" if number > 1 else "") + suffix
            target = (destination / name).resolve()
            if target.parent != destination:
                raise ValueError("Tên file không hợp lệ.")
            try:
                with source.open("rb") as data, target.open("xb") as saved:
                    shutil.copyfileobj(data, saved)
            except FileExistsError:
                continue
            except OSError as exc:
                raise ValueError(f"Không ghi được file vào {destination}.") from exc
            return {"name": name, "path": str(target), "bytes": target.stat().st_size}
        raise ValueError("Quá nhiều bản trùng tên. Hãy dọn thư mục lưu.")

    @app.get("/api/projects/{id}/files/{file:path}")
    def file(id: str, file: str, download: bool = False):
        p = store.get(id)
        root = store.directory(id).resolve()
        if p.get("video_external") and file == p["video_file"]:
            # The in-place source lives outside the project directory; serve only the stored path.
            path = Path(p.get("video_path") or "")
            if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
                raise HTTPException(409, "Không tìm thấy video nguồn của dự án.")
        else:
            path = (root / file).resolve()
            if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() not in MEDIA_SUFFIXES:
                raise HTTPException(404)
        if file.startswith("renders/"):
            job_path = path.parent / "job.json"
            if not job_path.exists():
                raise HTTPException(409, "Bản xuất chưa hoàn thành.")
            record = json.loads(job_path.read_text(encoding="utf-8"))
            matches = (record.get("video_file") == p["video_file"] and record.get("audio_index") == p["audio_index"]) if record.get("kind") == "proxy" else record["revision"] == p["revision"]
            if record["status"] != "complete" or (not record.get('version') and not matches):
                raise HTTPException(409, "Bản xuất không còn khớp với dự án. Hãy xuất lại.")
        return FileResponse(path, filename=(p["name"] + path.suffix) if download else None)

    frontend = ROOT / "frontend/dist"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
