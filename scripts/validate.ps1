$ErrorActionPreference = "Stop"
& .\.venv\Scripts\Activate.ps1
new-earth-platform validate
ruff check src tests
mypy src
pytest
