"""Create a source/runtime ZIP with built frontend, without user data or models."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT/'frontend/dist/index.html').is_file():
    raise SystemExit('Build frontend first.')
files = set()
for folder in ('src', 'apps/dubbing_web', 'frontend/dist'):
    files.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
for name in ('LICENSE','README-DUBBING.vi.md','Setup.ps1','Start.bat','requirements-dubbing.lock.txt',
             'scripts/start.py','scripts/setup_tools.py','docs/IMPLEMENTATION_STATUS.vi.md'):
    files.add(ROOT/name)
if (ROOT/'apps/__init__.py').exists():
    files.add(ROOT/'apps/__init__.py')
output = ROOT/'artifacts'
output.mkdir(exist_ok=True)
archive = output/'vieneu-dubbing-windows.zip'
manifest = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(files):
        bundle.write(path, path.relative_to(ROOT).as_posix())
    bundle.writestr('SHA256SUMS.json', json.dumps(manifest, indent=2))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert all(not name.startswith(('data/', '.tools/', '.venv/')) for name in bundle.namelist())
print(f'{archive} ({archive.stat().st_size} bytes)')
