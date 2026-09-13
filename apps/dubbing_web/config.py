from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    data: Path
    host: str = "127.0.0.1"
    port: int = 7861

    @classmethod
    def from_env(cls):
        data = Path(os.environ.get("APP_DATA_DIR", ROOT / "data")).resolve()
        os.environ.setdefault("HF_HOME", str(data / "models"))
        temporary = Path(os.environ.get("APP_TEMP_DIR", data / "tmp")).resolve()
        temporary.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(temporary)
        return cls(data, os.environ.get("APP_HOST", "127.0.0.1"), int(os.environ.get("APP_PORT", "7861")))


def executable(name: str) -> str:
    configured = os.environ.get(name.upper() + "_BIN")
    found = configured or shutil.which(name)
    if not found:
        suffix = ".exe" if os.name == "nt" else ""
        candidate = ROOT / ".tools" / (name + suffix)
        if candidate.is_file():
            found = str(candidate)
    if not found:
        raise RuntimeError(f"Thiếu {name}. Cài công cụ hoặc đặt {name.upper()}_BIN.")
    return found
