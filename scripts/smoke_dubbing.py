"""Real CPU/offline smoke test. Run after downloading model once."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apps.dubbing_web.config import Settings
from apps.dubbing_web.jobs import Jobs
from apps.dubbing_web.store import Store

settings = Settings.from_env()
jobs = Jobs(Store(settings.data))
started = time.perf_counter()
try:
    engine = jobs.load_model()
    loaded = time.perf_counter()
    result = engine.infer("Xin chào, đây là kiểm tra giọng đọc chạy trên máy.", voice="Kim Thanh")
    finished = time.perf_counter()
    assert len(result) > 0
    print(json.dumps({"offline": os.environ.get("HF_HUB_OFFLINE") == "1", "model_load_seconds": round(loaded-started, 2),
                      "synthesis_seconds": round(finished-loaded, 2), "audio_seconds": round(len(result)/48000, 2)}, ensure_ascii=True))
finally:
    jobs.shutdown()
