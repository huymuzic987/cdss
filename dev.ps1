Set-Location -Path $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CDSS Efficient Dev Server Launcher    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Start local PostgreSQL via Docker Desktop or WSL Docker
Write-Host "`n[1/4] Starting PostgreSQL container..." -ForegroundColor Yellow

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

# 2. Wait for DB to be healthy/ready on port 54321
Write-Host "[2/4] Waiting for database connection on port 54321..." -ForegroundColor Yellow
$retry = 0
$dbReady = $false
while ($retry -lt 30) {
    uv run python -c "import psycopg2; from backups.dump import _database_url; conn=psycopg2.connect(_database_url())" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $dbReady = $true
        break
    }
    Start-Sleep -Seconds 1
    $retry++
}

if (-not $dbReady) {
    Write-Host "Error: Could not connect to PostgreSQL on port 54321." -ForegroundColor Red
    Write-Host "Make sure Docker Desktop or WSL Docker daemon is running." -ForegroundColor Red
    exit 1
}
Write-Host "-> Database connection established!" -ForegroundColor Green

# 3. Run Alembic schema migrations
Write-Host "`n[3/4] Applying latest Alembic schema migrations..." -ForegroundColor Yellow
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "Alembic upgrade failed (likely orphaned revision). Stamping head..." -ForegroundColor Yellow
    uv run alembic stamp --purge head
    uv run alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Alembic migration failed." -ForegroundColor Red
        exit 1
    }
}

# 4. Overwrite DB data with seed.sql
Write-Host "`n[4/4] Overwriting database data with backups/seed.sql..." -ForegroundColor Yellow
uv run python -c "import psycopg2; from backups.dump import _database_url; conn=psycopg2.connect(_database_url()); cur=conn.cursor(); sql=open('backups/seed.sql', encoding='utf-8').read(); cur.execute(sql); conn.commit(); print('Database seeded successfully!')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Seeding database failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Database Ready! Starting Servers...   " -ForegroundColor Green
Write-Host "  Backend  : http://localhost:8000      " -ForegroundColor Green
Write-Host "  Frontend : http://localhost:5173      " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Launch Backend & Frontend concurrently (cmd.exe handles pnpm script execution on Windows)
$backendProcess = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "cdss.main:app", "--reload" -PassThru -NoNewWindow
$frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "pnpm --prefix frontend dev" -PassThru -NoNewWindow

try {
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`nStopping dev servers..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force 2>$null
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force 2>$null
    }
}
