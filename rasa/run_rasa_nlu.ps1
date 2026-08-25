# run_rasa_nlu.ps1 - Offline NLU chatbot: train (if needed) then open Inspector
#
# Usage:  .\run_rasa_nlu.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"

if (!(Test-Path $venvPython)) {
    Write-Host "Venv not found at $venvPython" -ForegroundColor Red
    Write-Host "Run: .\setup.ps1"
    exit 1
}

Set-Location $ScriptDir

# Load RASA_LICENSE from .env if present
if (Test-Path (Join-Path $ScriptDir ".env")) {
    Get-Content (Join-Path $ScriptDir ".env") | ForEach-Object {
        $line = $_.Trim()
        if ($line -and !$line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
            }
        }
    }
}

# Ensure NLU mode files (training happens below, unconditionally)
$configPath = Join-Path $ScriptDir "config.yml"
if (!(Select-String -Path $configPath -Pattern "DIETClassifier" -Quiet)) {
    Write-Host "Switching to NLU mode..." -ForegroundColor Yellow
    & "$ScriptDir\switch_mode.ps1" -Mode nlu -SkipTrain
}
if (!(Select-String -Path $configPath -Pattern "DIETClassifier" -Quiet)) {
    Write-Host "ERROR: Failed to activate NLU mode" -ForegroundColor Red
    exit 1
}

# Always train a fresh complete model (NLU-only archives have no core and break the bot)
Write-Host "Training model..." -ForegroundColor Yellow
uv run rasa train
if ($LASTEXITCODE -ne 0) { Write-Host "Training failed" -ForegroundColor Red; exit 1 }

# Keep only the newest model archive
$models = Get-ChildItem (Join-Path $ScriptDir "models") -Filter "*.tar.gz" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending
if ($models.Count -gt 1) {
    $models | Select-Object -Skip 1 | Remove-Item -Force
}

# Flows call Python actions (stats queries) via :5055 - reuse one if running,
# otherwise start a hidden one and stop it when this script exits.
$actionProc = $null
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:5055/health" -TimeoutSec 2 | Out-Null
} catch {
    $actionProc = Start-Process $venvPython -ArgumentList "-m rasa_sdk --actions actions --port 5055" `
        -WorkingDirectory $ScriptDir `
        -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

try {
    Write-Host ""
    Write-Host "Opening Rasa Inspector at http://localhost:5005 (Ctrl+C to stop)" -ForegroundColor Cyan
    uv run rasa inspect
} finally {
    if ($actionProc) {
        Stop-Process -Id $actionProc.Id -Force -ErrorAction SilentlyContinue
    }
}
