"""Local voice metadata. Inference shares the application's single CPU worker."""
import hashlib
import json
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .store import Conflict


class VoiceEdit(BaseModel):
    revision: int = 0
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    gender: str = Field(default="", max_length=50)
    region: str = Field(default="", max_length=50)
    style: str = Field(default="", max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=30)
    favorite: bool = False
    sample_text: str = Field(default="Xin chào, đây là giọng đọc mẫu cho bản lồng tiếng của bạn.", min_length=1, max_length=500)


def install_library(app, store, jobs, presets, get_dictionary):
    router = APIRouter(prefix="/api/library")
    with store.connection() as db:
        db.execute("CREATE TABLE IF NOT EXISTS voice_metadata (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    samples = {}
    lock = threading.RLock()
    cache = store.root / "samples"
    cache.mkdir(exist_ok=True)

    def voice(id):
        if id not in presets:
            raise KeyError(id)
        default = VoiceEdit(name=id, description=presets[id].get("description", ""),
                            gender={"male":"Nam", "female":"Nữ"}.get(presets[id].get("gender"), ""), region=presets[id].get("region", ""),
                            style={"tin_tuc":"Tin tức", "doc_truyen":"Kể chuyện", "tu_nhien":"Tự nhiên"}.get(presets[id].get("style"), presets[id].get("style", ""))).model_dump()
        with store.connection() as db:
            row = db.execute("SELECT data FROM voice_metadata WHERE id=?", (id,)).fetchone()
        return {**default, **(json.loads(row[0]) if row else {}), "id": id}

    @router.get("/voices")
    def voices():
        return [voice(id) for id in presets]

    @router.put("/voices/{id}")
    def edit(id: str, values: VoiceEdit):
        if not values.name.strip() or not values.sample_text.strip() or any(len(t) > 100 for t in values.tags):
            raise ValueError("Tên, câu mẫu hoặc thẻ không hợp lệ.")
        with store.lock, store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = voice(id)
            if current["revision"] != values.revision:
                raise Conflict("Thông tin giọng đã thay đổi. Hãy nạp lại.")
            data = values.model_dump()
            data["revision"] += 1
            db.execute("INSERT OR REPLACE INTO voice_metadata VALUES (?, ?)", (id, json.dumps(data, ensure_ascii=False)))
        return voice(id)

    @router.post("/voices/{id}/sample")
    def sample(id: str):
        current = voice(id)
        from .pronunciation import spoken_text
        text = spoken_text(current["sample_text"], get_dictionary()["rules"])
        key = hashlib.sha256(json.dumps(["library-v2", id, text], ensure_ascii=False).encode()).hexdigest()
        path = cache / (key + ".wav")
        with lock:
            if path.exists():
                return {"id": key, "status": "complete"}
            if key in samples and samples[key]["status"] in ("queued", "running"):
                return dict(samples[key])
            if any(s["status"] in ("queued", "running") for s in samples.values()):
                raise ValueError("Đang tạo một mẫu giọng. Hãy đợi hoàn tất.")
            state = {"id": key, "status": "queued"}
            samples[key] = state
            def work():
                temporary = path.with_suffix(".tmp.wav")
                try:
                    import soundfile as sf
                    state["status"] = "running"
                    wav = jobs.load_model().infer(text, voice=id)
                    if not len(wav):
                        raise ValueError("Model trả về âm thanh rỗng.")
                    sf.write(temporary, wav, 48000)
                    temporary.replace(path)
                    state["status"] = "complete"
                except Exception as exc:
                    state.update(status="failed", message=str(exc))
                finally:
                    temporary.unlink(missing_ok=True)
            jobs.pool.submit(work)
            return dict(state)

    @router.get("/samples/{key}")
    def sample_status(key: str):
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise KeyError(key)
        if (cache / (key + ".wav")).is_file():
            return {"id": key, "status": "complete"}
        if key not in samples:
            raise KeyError(key)
        return dict(samples[key])

    @router.get("/samples/{key}/audio")
    def sample_audio(key: str):
        if sample_status(key)["status"] != "complete":
            raise HTTPException(409, "Mẫu chưa sẵn sàng.")
        return FileResponse(cache / (key + ".wav"), media_type="audio/wav")

    app.include_router(router)
