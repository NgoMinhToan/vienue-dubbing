from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal

from .config import ROOT, Settings, executable
from .domain import Edit, parse_srt, voice_key, timing, cue_warnings
from .store import Store, Conflict
from .jobs import Jobs
from .media import inspect_video
from .library import install_library


class JobRequest(BaseModel):
    kind: Literal["generate", "mp3", "mkv", "proxy", "sample"] = "generate"
    cue_id: str | None = None
    allow_overlap: bool = False
    overflow_policy: Literal["keep", "skip"] | None = None


def create_app(settings=None):
    settings = settings or Settings.from_env()
    store = Store(settings.data)
    jobs = Jobs(store)
    presets = json.loads((ROOT / "src/vieneu/assets/voices_v3_turbo.json").read_text(encoding="utf-8"))
    voices = list(presets["presets"])

    def copy_upload(source, target):
        limit = int(os.environ.get("APP_MAX_VIDEO_BYTES", 20 * 1024**3))
        reserve = int(os.environ.get("APP_MIN_FREE_BYTES", 512 * 1024**2))
        total = 0
        while chunk := source.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ValueError(f"Video vượt giới hạn {limit // 1024**2} MB.")
            if shutil.disk_usage(settings.data).free < len(chunk) + reserve:
                raise ValueError("Không đủ dung lượng đĩa để lưu video. Hãy giải phóng dung lượng.")
            target.write(chunk)

    @asynccontextmanager
    async def lifespan(app):
        yield
        jobs.shutdown()

    app = FastAPI(title="VieNeu Dubbing", lifespan=lifespan)
    app.state.store, app.state.jobs = store, jobs
    install_library(app, store, jobs, presets["presets"])

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
        return [{"id": v, "description": presets["presets"][v].get("description", "")} for v in voices]

    @app.get("/api/projects")
    def projects():
        return [{"id": p["id"], "name": p["name"], "count": len(p["cues"]), "updated": p["updated"], "video_name": p["video_name"]} for p in store.list()]

    @app.post("/api/projects")
    def create(name: str = Form("Lồng tiếng mới"), video: UploadFile = File(...), srt: UploadFile = File(...)):
        if not name.strip() or len(name) > 200:
            raise ValueError("Tên dự án không hợp lệ.")
        raw = srt.file.read(10 * 1024 * 1024 + 1)
        if len(raw) > 10 * 1024 * 1024:
            raise ValueError("SRT quá lớn (tối đa 10 MB).")
        cues = parse_srt(raw)
        id, root = store.create()
        try:
            suffix = Path(video.filename or "").suffix.lower()
            if suffix not in (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"):
                raise ValueError("Định dạng video chưa hỗ trợ.")
            path = root / ("source" + suffix)
            with path.open("wb") as target:
                copy_upload(video.file, target)
            info = inspect_video(path)
            selected = next((a for a in info["audio_tracks"] if a["default"]), next(iter(info["audio_tracks"]), None))
            project = {"id": id, "revision": 1, "name": name, "voice": "Kim Thanh" if "Kim Thanh" in voices else voices[0],
                       "speed": 1, "auto_fit": True, "fit_limit": 1.6, "background": "duck",
                       "audio_index": selected["index"] if selected else None,
                       "video_name": Path(video.filename).name, "video_file": path.name, "media": info, "cues": cues}
            return describe(store.save(project))
        except Exception:
            shutil.rmtree(root)
            raise

    @app.get("/api/projects/{id}")
    def get(id: str):
        project = describe(store.get(id))
        saved = [j for j in jobs.items.values() if j["project"] == id and j["revision"] == project["revision"]]
        project["last_job"] = jobs.public(saved[-1]) if saved else None
        return project

    @app.put("/api/projects/{id}")
    def edit(id: str, values: Edit):
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
                    raw = srt.file.read(10 * 1024 * 1024 + 1)
                    if len(raw) > 10 * 1024 * 1024:
                        raise ValueError("SRT tối đa 10 MB.")
                    p["cues"] = parse_srt(raw)
                if video:
                    suffix = Path(video.filename or "").suffix.lower()
                    if suffix not in (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"):
                        raise ValueError("Định dạng video chưa hỗ trợ.")
                    new_path = store.directory(id) / ("source-" + uuid4().hex + suffix)
                    with new_path.open("wb") as target:
                        copy_upload(video.file, target)
                    info = inspect_video(new_path)
                    selected = next((a for a in info["audio_tracks"] if a["default"]), next(iter(info["audio_tracks"]), None))
                    p.update(video_file=new_path.name, video_name=Path(video.filename).name, media=info,
                             audio_index=selected["index"] if selected else None)
                p["revision"] += 1
                return describe(store.save(p, expected=revision))
            except Exception:
                if new_path:
                    new_path.unlink(missing_ok=True)
                raise

    @app.delete("/api/projects/{id}")
    def delete(id: str):
        store.get(id)
        if any(j["project"] == id and j["status"] in ("queued", "running") for j in jobs.items.values()):
            raise ValueError("Hãy dừng tác vụ trước khi xóa dự án.")
        store.delete(id)
        shutil.rmtree(store.directory(id))
        return {"ok": True}

    @app.post("/api/projects/{id}/cleanup")
    def cleanup(id: str, confirm: bool = False):
        if not confirm:
            raise ValueError("Cần xác nhận dọn bản xuất/cache cũ.")
        with jobs.lock:
            p = store.get(id)
            if any(j["project"] == id and j["status"] in ("queued", "running") for j in jobs.items.values()):
                raise ValueError("Đợi hoặc dừng tác vụ trước khi dọn dữ liệu.")
            root = store.directory(id).resolve()
            removed = 0
            # Keep current-revision outputs and a proxy matching the selected source track.
            for jid, record in list(jobs.items.items()):
                if record["project"] != id:
                    continue
                current = record["revision"] == p["revision"] and record["status"] == "complete"
                proxy = record["kind"] == "proxy" and record["status"] == "complete" and record.get("video_file") == p["video_file"] and record.get("audio_index") == p["audio_index"]
                if current or proxy:
                    continue
                folder = (root / "renders" / jid).resolve()
                if folder.parent != root / "renders":
                    continue
                if folder.is_dir():
                    removed += sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                    shutil.rmtree(folder)
                jobs.items.pop(jid, None)
            keys = {voice_key(c, p) + ".wav" for c in p["cues"]}
            for clip in (root / "clips").glob("*.wav"):
                if clip.name not in keys:
                    removed += clip.stat().st_size
                    clip.unlink()
            return {"removed_bytes": removed}

    @app.post("/api/projects/{id}/jobs")
    def submit(id: str, request: JobRequest):
        p = store.get(id)
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
        jobs.items[id]["cancel"].set()
        return {"ok": True}

    @app.get("/api/projects/{id}/files/{file:path}")
    def file(id: str, file: str, download: bool = False):
        p = store.get(id)
        root = store.directory(id).resolve()
        path = (root / file).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() not in (".mp3", ".mkv", ".mp4", ".mov", ".avi", ".webm", ".m4v", ".wav"):
            raise HTTPException(404)
        if file.startswith("renders/"):
            job_path = path.parent / "job.json"
            if not job_path.exists():
                raise HTTPException(409, "Bản xuất chưa hoàn thành.")
            record = json.loads(job_path.read_text(encoding="utf-8"))
            matches = (record.get("video_file") == p["video_file"] and record.get("audio_index") == p["audio_index"]) if record.get("kind") == "proxy" else record["revision"] == p["revision"]
            if record["status"] != "complete" or not matches:
                raise HTTPException(409, "Bản xuất không còn khớp với dự án. Hãy xuất lại.")
        return FileResponse(path, filename=(p["name"] + path.suffix) if download else None)

    frontend = ROOT / "frontend/dist"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
