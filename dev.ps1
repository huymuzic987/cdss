[CmdletBinding()]
param(
    [switch]$ForceSeed
)

Set-Location -Path $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CDSS Efficient Dev Server Launcher    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Helper function for fast TCP port check without spawning external processes
function Test-PortOpen([string]$HostName, [int]$Port, [int]$TimeoutMs = 300) {
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $asyncResult = $client.BeginConnect($HostName, $Port, $null, $null)
        if ($asyncResult.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            $client.EndConnect($asyncResult)
            $client.Close()
            return $true
        }
        $client.Close()
    } catch {}
    return $false
}

# 1. Check if DB container is already running and reachable
Write-Host "`n[1/3] Checking PostgreSQL container status..." -ForegroundColor Yellow

$dbAlreadyUp = Test-PortOpen "127.0.0.1" 54321 300

if ($dbAlreadyUp) {
    Write-Host "-> PostgreSQL is already listening on port 54321." -ForegroundColor Green
} else {
    Write-Host "Starting PostgreSQL container via Docker..." -ForegroundColor Yellow
    $dockerStarted = $false

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
}

# 2. Fast wait for DB to be healthy/ready on port 54321
Write-Host "[2/3] Waiting for database connection on port 54321..." -ForegroundColor Yellow
$retry = 0
$dbReady = $false

while ($retry -lt 30) {
    if (Test-PortOpen "127.0.0.1" 54321 200) {
        # Perform psycopg2 connection test only when TCP port is active
        uv run python -c "import psycopg2; from backups.dump import _database_url; conn=psycopg2.connect(_database_url())" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $dbReady = $true
            break
        }
    }
    Start-Sleep -Milliseconds 500
    $retry++
}

if (-not $dbReady) {
    Write-Host "Error: Could not connect to PostgreSQL on port 54321." -ForegroundColor Red
    Write-Host "Make sure Docker Desktop or WSL Docker daemon is running." -ForegroundColor Red
    exit 1
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
