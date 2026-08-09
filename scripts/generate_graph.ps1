$ErrorActionPreference = "Stop"
& .\.venv\Scripts\Activate.ps1
New-Item -ItemType Directory -Force artifacts\generated | Out-Null
new-earth-platform graph --format mermaid --output artifacts\generated\platform.mmd
Get-Content artifacts\generated\platform.mmd
