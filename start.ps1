# ChronoMate Desktop - Windows PowerShell Launcher
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   ChronoMate Desktop - Windows PowerShell Launcher " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Locate Python
$pyCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3 --version | Out-Null
        if ($LASTEXITCODE -eq 0) { $pyCmd = "py -3" }
    } catch {}
}
if (-not $pyCmd -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $pyCmd = "python"
}
if (-not $pyCmd -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
    $pyCmd = "python3"
}

if (-not $pyCmd) {
    Write-Host "[ERROR] Python 3 was not found. Please install Python from https://www.python.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 2. Virtual Environment
$venvActivate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if ($env:VIRTUAL_ENV) {
    Write-Host "[INFO] Active virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
    $runPy = "python"
    $runPip = "pip"
} elseif (Test-Path $venvActivate) {
    Write-Host "[INFO] Activating local virtual environment (.venv)..." -ForegroundColor Green
    & $venvActivate
    $runPy = "python"
    $runPip = "pip"
} else {
    $depCheck = & $pyCmd.Split(' ') -c "import PySide6, requests, reportlab, openpyxl, pygame" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[SETUP] Creating local virtual environment (.venv)..." -ForegroundColor Yellow
        & $pyCmd.Split(' ') -m venv .venv
        if (Test-Path $venvActivate) {
            & $venvActivate
            $runPy = "python"
            $runPip = "pip"
            Write-Host "[INFO] Virtual environment created and activated." -ForegroundColor Green
        } else {
            $runPy = $pyCmd
            $runPip = "$pyCmd -m pip"
        }
    } else {
        $runPy = $pyCmd
        $runPip = "$pyCmd -m pip"
    }
}

# 3. Check Dependencies
Write-Host "[CHECK] Verifying application dependencies..." -ForegroundColor Cyan
$env:PYGAME_HIDE_SUPPORT_PROMPT = "1"
$check = & $runPy.Split(' ') -c "import PySide6, requests, reportlab, openpyxl, pygame" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INSTALL] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    & $runPip.Split(' ') install -r requirements.txt
    Write-Host "[OK] Dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "[OK] All dependencies are already installed and up to date." -ForegroundColor Green
}

# 4. Launch Application
Write-Host "====================================================" -ForegroundColor Green
Write-Host "   Launching ChronoMate Desktop...                  " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
& $runPy.Split(' ') main.py $args
