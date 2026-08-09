$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
new-earth-platform validate
pytest
Write-Host "New Earth Platform Core bootstrap complete." -ForegroundColor Green
