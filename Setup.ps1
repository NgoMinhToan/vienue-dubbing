$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 and enable PATH, then retry.' }
}
& ./.venv/Scripts/python.exe -m pip install -r requirements-dubbing.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
& ./.venv/Scripts/python.exe scripts/setup_tools.py
if ($LASTEXITCODE -ne 0) { throw 'Media tools installation failed.' }
if (-not (Test-Path 'frontend/dist/index.html')) {
    Push-Location frontend
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
Write-Host 'Setup complete. Open Start.bat.'
