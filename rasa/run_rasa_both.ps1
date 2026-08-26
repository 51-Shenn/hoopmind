# run_rasa_both.ps1 - Run the NLU and LLM assistants side by side (for demos).
#
# The single-mode launchers cannot be used together: they share config.yml /
# domain.yml, both retrain on start, run_rasa_nlu.ps1 prunes every model archive
# but the newest, both bind :5005, and both reuse ONE action server on :5055 --
# so whichever starts first decides HOOPMIND_GROUND_ANSWERS for both bots.
#
# This script avoids all of that: it trains both models up front under fixed
# names, serves each by explicit path (a model archive carries its own config
# and domain, so config.yml is irrelevant at serve time), and gives each bot its
# own action server and endpoints file.
#
#   :8080  Gemini key-rotation proxy   (LLM only)
#   :5055  action server, grounding OFF -> NLU bot   (endpoints_nlu.yml)
#   :5056  action server, grounding ON  -> LLM bot   (endpoints_llm.yml)
#   :5005  NLU Inspector      :5006  LLM Inspector
#
# Usage:
#   .\run_rasa_both.ps1                                # train both, launch both
#   .\run_rasa_both.ps1 -SkipTrain                     # reuse existing archives
#   .\run_rasa_both.ps1 -NluPort 5006 -LlmPort 5005    # swap the Inspector ports

param(
    [int]$NluPort = 5005,
    [int]$LlmPort = 5006,
    [switch]$SkipTrain
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"

# Action-server ports are baked into endpoints_{nlu,llm}.yml - change both together.
$NluActionPort = 5055
$LlmActionPort = 5056
$ProxyPort     = 8080

$NluModel = "models/hoopmind_nlu.tar.gz"
$LlmModel = "models/hoopmind_llm.tar.gz"

if (!(Test-Path $venvPython)) {
    Write-Host "Venv not found at $venvPython" -ForegroundColor Red
    Write-Host "Run: .\setup.ps1"
    exit 1
}

Set-Location $ScriptDir

# -- Helpers -------------------------------------------------
function Test-PortInUse([int]$Port) {
    $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    return [bool]($listeners | Where-Object { $_.Port -eq $Port })
}

# uv and pwsh spawn children, so kill the whole tree or the port stays held.
function Stop-Tree($proc) {
    if ($proc -and !$proc.HasExited) {
        & taskkill /PID $proc.Id /T /F 2>&1 | Out-Null
    }
}

function Wait-ForHealth([string]$Url, [int]$TimeoutSec = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -TimeoutSec 2 -ErrorAction Stop | Out-Null
            return $true
        } catch {
            # A 404 still proves something is listening and speaking HTTP.
            if ($_.Exception.Response.StatusCode.value__ -eq 404) { return $true }
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

# -- Load .env (RASA_LICENSE + Gemini keys; children inherit these) ----
$envPath = Join-Path $ScriptDir ".env"
if (!(Test-Path $envPath)) {
    Write-Host ".env not found at $envPath" -ForegroundColor Red
    exit 1
}
Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and !$line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Length -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

# -- Validate Gemini keys (the LLM bot is useless without them) --------
$keys = @()
if ($env:GEMINI_API_KEY -and $env:GEMINI_API_KEY -ne "your-primary-key-here") { $keys += $env:GEMINI_API_KEY }
for ($i = 1; $i -le 9; $i++) {
    $k = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY_$i", "Process")
    if ($k -and $k -notlike "your-*-key-here") { $keys += $k }
}
if ($keys.Count -eq 0) {
    Write-Host "ERROR: No valid Gemini API keys in .env - the LLM bot cannot run." -ForegroundColor Red
    Write-Host "Set GEMINI_API_KEY and/or GEMINI_API_KEY_1..9, or use .\run_rasa_nlu.ps1 for NLU only."
    exit 1
}
Write-Host "Found $($keys.Count) Gemini API key(s) - proxy will rotate on failure" -ForegroundColor Green

# -- All five ports must be free ---------------------------------------
if ($NluPort -eq $LlmPort) {
    Write-Host "ERROR: -NluPort and -LlmPort must differ (both are $NluPort)" -ForegroundColor Red
    exit 1
}
$busy = @()
foreach ($p in @($ProxyPort, $NluActionPort, $LlmActionPort, $NluPort, $LlmPort)) {
    if (Test-PortInUse $p) { $busy += $p }
}
if ($busy.Count -gt 0) {
    Write-Host "ERROR: port(s) already in use: $($busy -join ', ')" -ForegroundColor Red
    Write-Host "Close any running run_rasa_*.ps1 windows and stray action servers, then retry."
    exit 1
}

$proxy = $null; $nluActions = $null; $llmActions = $null; $nluBot = $null; $llmBot = $null

try {
    # -- Proxy first: LLM-mode training embeds flow descriptions through it --
    Write-Host "Starting Gemini key-rotation proxy on :$ProxyPort..." -ForegroundColor Cyan
    $proxy = Start-Process $venvPython -ArgumentList "gemini_proxy.py" `
        -WorkingDirectory $ScriptDir -PassThru -WindowStyle Hidden
    if (!(Wait-ForHealth "http://127.0.0.1:$ProxyPort/status" 20)) {
        Write-Host "Proxy failed to start - aborting" -ForegroundColor Red
        exit 1
    }
    Write-Host "Proxy is alive" -ForegroundColor Green

    # -- Train both models under fixed names -------------------------------
    if ($SkipTrain) {
        Write-Host "Skipping training (-SkipTrain)" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "[1/2] Training NLU model -> $NluModel" -ForegroundColor Yellow
        & "$ScriptDir\switch_mode.ps1" -Mode nlu -SkipTrain
        uv run rasa train --fixed-model-name hoopmind_nlu
        if ($LASTEXITCODE -ne 0) { Write-Host "NLU training failed - aborting" -ForegroundColor Red; exit 1 }

        Write-Host ""
        Write-Host "[2/2] Training LLM model -> $LlmModel" -ForegroundColor Yellow
        & "$ScriptDir\switch_mode.ps1" -Mode llm -SkipTrain
        uv run rasa train --fixed-model-name hoopmind_llm
        if ($LASTEXITCODE -ne 0) { Write-Host "LLM training failed - aborting" -ForegroundColor Red; exit 1 }
    }

    foreach ($m in @($NluModel, $LlmModel)) {
        if (!(Test-Path (Join-Path $ScriptDir $m))) {
            Write-Host "ERROR: $m is missing. Re-run without -SkipTrain." -ForegroundColor Red
            exit 1
        }
    }

    # -- One action server per bot, differing only in grounding ------------
    # compose_answer() in actions/llm_answer.py reads HOOPMIND_GROUND_ANSWERS
    # from its own process at call time, so a shared server would leak the
    # LLM bot's grounding into the "fully offline" NLU demo.
    Write-Host ""
    Write-Host "Starting action server :$NluActionPort (grounding OFF)..." -ForegroundColor Cyan
    [Environment]::SetEnvironmentVariable("HOOPMIND_GROUND_ANSWERS", $null, "Process")
    $nluActions = Start-Process $venvPython -ArgumentList "-m rasa_sdk --actions actions --port $NluActionPort" `
        -WorkingDirectory $ScriptDir -PassThru -WindowStyle Hidden

    Write-Host "Starting action server :$LlmActionPort (grounding ON)..." -ForegroundColor Cyan
    [Environment]::SetEnvironmentVariable("HOOPMIND_GROUND_ANSWERS", "true", "Process")
    $llmActions = Start-Process $venvPython -ArgumentList "-m rasa_sdk --actions actions --port $LlmActionPort" `
        -WorkingDirectory $ScriptDir -PassThru -WindowStyle Hidden
    [Environment]::SetEnvironmentVariable("HOOPMIND_GROUND_ANSWERS", $null, "Process")

    foreach ($p in @($NluActionPort, $LlmActionPort)) {
        if (!(Wait-ForHealth "http://127.0.0.1:$p/health" 30)) {
            Write-Host "Action server on :$p did not come up - aborting" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "Both action servers are alive" -ForegroundColor Green

    # -- Each bot in its own window, served from its own archive ------------
    $psExe = (Get-Process -Id $PID).Path
    if (!$psExe) { $psExe = "powershell.exe" }

    function Start-Bot([string]$Title, [string]$Model, [string]$Endpoints, [int]$Port) {
        $cmd = "`$Host.UI.RawUI.WindowTitle='$Title'; Set-Location '$ScriptDir'; " +
               "uv run rasa inspect -m '$Model' --endpoints '$Endpoints' -p $Port -i 127.0.0.1 --cors '*'"
        return Start-Process $psExe -ArgumentList "-NoExit", "-Command", $cmd -PassThru
    }

    Write-Host ""
    Write-Host "Launching both Inspectors..." -ForegroundColor Cyan
    $nluBot = Start-Bot "HoopMind NLU :$NluPort" $NluModel "endpoints_nlu.yml" $NluPort
    $llmBot = Start-Bot "HoopMind LLM :$LlmPort" $LlmModel "endpoints_llm.yml" $LlmPort

    Write-Host ""
    Write-Host "--------------------------------------------"
    Write-Host "  NLU (offline)  http://127.0.0.1:$NluPort/webhooks/inspector/inspect.html" -ForegroundColor Green
    Write-Host "  LLM (Gemini)   http://127.0.0.1:$LlmPort/webhooks/inspector/inspect.html" -ForegroundColor Green
    Write-Host "--------------------------------------------"
    Write-Host "Each bot has its own window - Ctrl+C there stops just that one."
    Write-Host "config.yml/domain.yml are left in LLM mode; the running bots ignore them." -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to stop everything"
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    Stop-Tree $llmBot
    Stop-Tree $nluBot
    Stop-Tree $llmActions
    Stop-Tree $nluActions
    Stop-Tree $proxy
}
