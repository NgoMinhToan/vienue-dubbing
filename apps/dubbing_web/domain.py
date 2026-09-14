import hashlib
import json
import re
from uuid import uuid4
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Cue(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=10000)
    original_text: str | None = None
    voice: str | None = None
    speed: float | None = Field(default=None, ge=0.5, le=3)

    @model_validator(mode="after")
    def valid(self):
        if self.end <= self.start or not self.text.strip():
            raise ValueError("Mốc kết thúc phải sau bắt đầu và câu phải có nội dung.")
        return self


class Edit(BaseModel):
    revision: int
    name: str = Field(min_length=1, max_length=200)
    voice: str
    speed: float = Field(default=1, ge=0.5, le=3)
    auto_fit: bool = True
    fit_limit: float = Field(default=1.6, ge=1, le=3)
    background: Literal["duck", "original_duck", "original", "quiet", "off"] = "duck"
    audio_index: int | None = None
    cues: list[Cue] = Field(max_length=10000)


STAMP = re.compile(r"^(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})$")


def seconds(value):
    match = STAMP.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Mốc thời gian không hợp lệ: {value}")
    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000


def parse_srt(raw: bytes) -> list[dict]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("SRT phải dùng UTF-8. Hãy lưu lại file bằng UTF-8.") from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    result = []
    for number, block in enumerate(re.split(r"\n\s*\n", text), 1):
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines.pop(0)
        try:
            a, b = lines[0].split("-->")
            body = re.sub(r"<[^>]*>", "", " ".join(lines[1:])).strip()
            result.append(Cue(start=seconds(a), end=seconds(b), text=body, original_text=body).model_dump())
        except (ValueError, IndexError) as exc:
            raise ValueError(f"SRT lỗi ở mục {number}: {exc}") from exc
    if not result or len(result) > 10000:
        raise ValueError("SRT cần có từ 1 đến 10.000 câu.")
    return sorted(result, key=lambda c: c["start"])


def voice_key(cue, project):
    payload = ["v3turbo-fp32-v1", cue["text"], cue.get("voice") or project["voice"]]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def cue_warnings(cues, duration):
    result = []
    ordered = sorted(cues, key=lambda c: c["start"])
    latest_end = 0
    for i, cue in enumerate(ordered):
        if cue["start"] < latest_end:
            result.append({"cue": i + 1, "message": "Mốc SRT chồng với câu trước."})
        if cue["end"] > duration:
            result.append({"cue": i + 1, "message": "Mốc SRT vượt thời lượng video."})
        latest_end = max(latest_end, cue["end"])
    return result


def timing(duration, start, next_start, speed, auto_fit=True, limit=1.6):
    window = max(0, next_start - start)
    required = max(1, duration / speed / window) if window > 0 else float("inf")
    actual = min(3, speed * min(limit, required)) if auto_fit and window > 0 else speed
    length = duration / actual
    return {"speed": actual, "duration": length, "overflow": max(0, length - window)}
