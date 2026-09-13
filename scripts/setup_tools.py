"""Install portable media tools into this checkout, never system directories."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1] / ".tools"


def download(url, name, expected=None):
    path = ROOT / name
    with urllib.request.urlopen(url, timeout=120) as response, path.open("wb") as out:
        shutil.copyfileobj(response, out)
    if expected and hashlib.file_digest(path.open("rb"), "sha256").hexdigest() != expected:
        raise RuntimeError("Checksum mismatch: " + name)
    with zipfile.ZipFile(path) as archive:
        dest = ROOT / (name + "-unpacked")
        # Check every resolved member before extraction.
        for member in archive.namelist():
            if not (dest / member).resolve().is_relative_to(dest.resolve()):
                raise RuntimeError("Unsafe archive path")
        archive.extractall(dest)
    return dest


if __name__ == "__main__":
    if os.name != "nt":
        print("Install ffmpeg and mkvtoolnix using your Linux package manager.")
        raise SystemExit(0)
    ROOT.mkdir(exist_ok=True)
    if not (ROOT / "ffmpeg.exe").exists() or not (ROOT / "ffprobe.exe").exists():
        # Fixed release, downloadable from the publisher's GitHub mirror.
        base = "https://github.com/GyanD/codexffmpeg/releases/download/9.0.1/"
        directory = download(base + "ffmpeg-9.0.1-essentials_build.zip", "ffmpeg.zip")
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            shutil.copy2(next(directory.rglob(name)), ROOT / name)
    if not (ROOT / "mkvmerge.exe").exists():
        directory = download("https://mkvtoolnix.download/windows/releases/101.0/mkvtoolnix-64-bit-101.0.zip", "mkv.zip",
                             "59a807b45b34ac524dfdef61edcf0642ee9bd6b08c130cfc078532c362569abc")
        source = next(directory.rglob("mkvmerge.exe")).parent
        shutil.copytree(source, ROOT, dirs_exist_ok=True)
    print("Media tools ready:", ROOT)
