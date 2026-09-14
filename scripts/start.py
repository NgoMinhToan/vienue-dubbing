"""Cross-platform launcher. Use --headless in containers."""
import argparse
import os
from pathlib import Path
import sys
import threading
import urllib.request
import time
import webbrowser
import socket

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def open_when_ready(url):
    for _ in range(60):
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=1):
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    from apps.dubbing_web.config import Settings, executable
    from apps.dubbing_web.api import create_app
    import uvicorn
    settings = Settings.from_env()
    try:
        for name in ("ffmpeg", "ffprobe", "mkvmerge"):
            executable(name)
        if not (ROOT / "frontend/dist/index.html").is_file():
            raise RuntimeError("Chua co giao dien da build. Hay chay Setup.ps1 truoc.")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.bind((settings.host, settings.port))
    except (RuntimeError, OSError) as exc:
        print(f"Khong the khoi dong: {exc}\nNeu cong {settings.port} dang duoc dung, mo ban dang chay hoac doi APP_PORT.")
        sys.exit(1)
    if not args.headless:
        threading.Thread(target=open_when_ready, args=(f"http://127.0.0.1:{settings.port}",), daemon=True).start()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
