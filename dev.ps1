Set-Location -Path $PSScriptRoot
uv run uvicorn cdss.main:app --reload
