# run_rasa_llm.ps1 - Start Rasa with Gemini key-rotation proxy
#
# 1. Reads API keys from .env (in this directory)
# 2. Starts gemini_proxy.py in background (rotates keys on failure)
# 3. Starts Rasa action server + Rasa shell (LLM mode)
#
# Usage:  .\run_rasa_llm.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"

if (!(Test-Path $venvPython)) {
    Write-Host "Venv not found at $venvPython" -ForegroundColor Red
    Write-Host "Run: .\setup.ps1"
    exit 1
}

# Run everything from the script's directory so relative paths resolve
Set-Location $ScriptDir

# -- Load .env -----------------------------------------------
function Load-EnvFile($path) {
    if (!(Test-Path $path)) { Write-Host ".env not found at $path"; exit 1 }
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and !$line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $val = $parts[1].Trim()
                [Environment]::SetEnvironmentVariable($key, $val, "Process")
            }
        }
    }
}

Load-EnvFile (Join-Path $ScriptDir ".env")

# LLM mode grounds custom-action answers in Gemini (actions/llm_answer.py)
[Environment]::SetEnvironmentVariable("HOOPMIND_GROUND_ANSWERS", "true", "Process")

# -- Validate keys -------------------------------------------
$keys = @()
$primary = $env:GEMINI_API_KEY
if ($primary -and $primary -ne "your-primary-key-here") { $keys += $primary }
for ($i = 1; $i -le 9; $i++) {
    $k = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY_$i", "Process")
    if ($k -and $k -ne "your-$(@('second','third','fourth','fifth','sixth','seventh','eighth','ninth')[$i-1])-key-here") {
        $keys += $k
    }
}

if ($keys.Count -eq 0) {
    Write-Host "ERROR: No valid API keys found in .env" -ForegroundColor Red
    Write-Host "Set GEMINI_API_KEY and/or GEMINI_API_KEY_1..3 in ..\.env"
    exit 1
}
Write-Host "Found $($keys.Count) API key(s) - proxy will rotate on failure" -ForegroundColor Green

# -- Start proxy (BEFORE training: LLM-mode train embeds flows via this proxy)
Write-Host "Starting Gemini key-rotation proxy on :8080..." -ForegroundColor Cyan
$proxy = Start-Process $venvPython -ArgumentList "gemini_proxy.py" `
    -WorkingDirectory $ScriptDir `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2

$proxyOk = $false
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1beta/models" -Method GET -TimeoutSec 3 -ErrorAction Stop | Out-Null
    $proxyOk = $true
} catch {
    # 404 on /v1beta/models is fine - means proxy is running
    if ($_.Exception.Response.StatusCode.value__ -eq 404) { $proxyOk = $true }
}
if ($proxyOk) {
    Write-Host "Proxy is alive" -ForegroundColor Green
} else {
    Write-Host "Proxy failed to start - aborting" -ForegroundColor Red
    exit 1
}

# -- Ensure LLM mode files, then always train fresh ----------
$configPath = Join-Path $ScriptDir "config.yml"
if (!(Select-String -Path $configPath -Pattern "CompactLLMCommandGenerator" -Quiet)) {
    Write-Host "Switching to LLM mode..." -ForegroundColor Yellow
    & "$ScriptDir\switch_mode.ps1" -Mode llm -SkipTrain
}

Write-Host "Training model..." -ForegroundColor Yellow
uv run rasa train
if ($LASTEXITCODE -ne 0) {
    Write-Host "Training failed - aborting" -ForegroundColor Red
    exit 1
}

# -- Start Rasa ----------------------------------------------
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
    Write-Host "Opening Rasa Inspector (LLM mode) at http://localhost:5005 (Ctrl+C to stop)" -ForegroundColor Cyan
    Write-Host "--------------------------------------------"
    uv run rasa inspect --port 5005 -i 127.0.0.1 --cors "*"
} finally {
    Stop-Process -Id $proxy.Id -Force -ErrorAction SilentlyContinue
    if ($actionProc) {
        Stop-Process -Id $actionProc.Id -Force -ErrorAction SilentlyContinue
    }
}
