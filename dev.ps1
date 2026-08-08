[CmdletBinding()]
param(
    [switch]$ForceSeed
)

Set-Location -Path $PSScriptRoot

$databaseUrl = uv run python scripts/dev_database.py resolve
if ($LASTEXITCODE -ne 0) {
    Write-Error "Could not resolve the development database URL."
    exit $LASTEXITCODE
}
$env:DATABASE_URL = $databaseUrl.Trim()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CDSS Efficient Dev Server Launcher    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Start the DB container when available
Write-Host "`n[1/3] Checking PostgreSQL container status..." -ForegroundColor Yellow

$dockerStarted = $false

Write-Host "Starting PostgreSQL container via Docker..." -ForegroundColor Yellow

# Try native Docker (Docker Desktop)
if (Get-Command "docker" -ErrorAction SilentlyContinue) {
    docker compose up -d postgres 2>$null
    if ($LASTEXITCODE -eq 0) { $dockerStarted = $true }
    else {
        docker compose up -d 2>$null
        if ($LASTEXITCODE -eq 0) { $dockerStarted = $true }
        else {
            if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
                docker-compose up -d 2>$null
                if ($LASTEXITCODE -eq 0) { $dockerStarted = $true }
            }
        }
    }
}

# Fallback to WSL Docker if native docker is not running or failed
if (-not $dockerStarted -and (Get-Command "wsl" -ErrorAction SilentlyContinue)) {
    wsl docker compose up -d postgres 2>$null
    if ($LASTEXITCODE -eq 0) { $dockerStarted = $true }
    else {
        wsl docker compose up -d 2>$null
        if ($LASTEXITCODE -eq 0) { $dockerStarted = $true }
        else {
            wsl docker-compose up -d 2>$null
            if ($LASTEXITCODE -eq 0) { $dockerStarted = $true }
        }
    }
}

# 2. Wait for DB to be healthy/ready
Write-Host "[2/3] Waiting for database connection on port 54321..." -ForegroundColor Yellow
uv run python scripts/dev_database.py wait
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "-> Database connection established!" -ForegroundColor Green

# 3. Smart database seed & migration check
Write-Host "`n[3/3] Checking database seed status..." -ForegroundColor Yellow
$ensureSeedArgs = @("run", "python", "scripts/ensure_seed.py")
if ($ForceSeed) {
    $ensureSeedArgs += "--force"
}

uv @ensureSeedArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Database seed check failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Database Ready! Starting Servers...   " -ForegroundColor Green
Write-Host "  Backend  : http://localhost:8000      " -ForegroundColor Green
Write-Host "  Frontend : http://localhost:5173      " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Launch Backend & Frontend concurrently (limit uvicorn reload scope to 'src' to avoid watching node_modules & .venv)
$backendProcess = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "cdss.main:app", "--reload", "--reload-dir", "src" -PassThru -NoNewWindow
$frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "pnpm --prefix frontend dev" -PassThru -NoNewWindow

function Stop-Tree([int]$ProcessId) {
    if ($ProcessId -gt 0) {
        cmd.exe /c "taskkill /F /T /PID $ProcessId 2>nul" | Out-Null
    }
}

try {
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`nStopping dev servers..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Tree -ProcessId $backendProcess.Id
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Tree -ProcessId $frontendProcess.Id
    }
}
