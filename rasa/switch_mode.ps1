# Switch between LLM and NLU modes for HoopMind Rasa chatbot.
# Usage: .\switch_mode.ps1 [llm|nlu] [-SkipTrain]

param(
    [ValidateSet("llm", "nlu")]
    [string]$Mode,
    [switch]$SkipTrain
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $ScriptDir "config.yml"

if ([string]::IsNullOrEmpty($Mode)) {
    if (Select-String -Path $configPath -Pattern "CompactLLMCommandGenerator" -Quiet) {
        Write-Host "Current mode: llm"
    } elseif (Select-String -Path $configPath -Pattern "DIETClassifier" -Quiet) {
        Write-Host "Current mode: nlu"
    } else {
        Write-Host "Current mode: unknown"
    }
    Write-Host "Usage: .\switch_mode.ps1 -Mode [llm|nlu]"
    exit 0
}

switch ($Mode) {
    "llm" {
        Copy-Item (Join-Path $ScriptDir "config_llm.yml") $configPath -Force
        Copy-Item (Join-Path $ScriptDir "domain_modes\domain_llm.yml") (Join-Path $ScriptDir "domain.yml") -Force
        Write-Host "Switched to LLM mode (Gemini + Flows)" -ForegroundColor Green
    }
    "nlu" {
        Copy-Item (Join-Path $ScriptDir "config_nlu.yml") $configPath -Force
        Copy-Item (Join-Path $ScriptDir "domain_modes\domain_nlu.yml") (Join-Path $ScriptDir "domain.yml") -Force
        Write-Host "Switched to NLU mode (DIETClassifier + TEDPolicy)" -ForegroundColor Green
    }
}

if ($SkipTrain) {
    Write-Host "Skipping training (-SkipTrain)" -ForegroundColor Gray
    exit 0
}

Write-Host "Training with new config..." -ForegroundColor Yellow
Push-Location $ScriptDir
try {
    & uv run rasa train
} finally {
    Pop-Location
}
if ($LASTEXITCODE -eq 0) {
    Write-Host "Training complete - ready to use" -ForegroundColor Green
} else {
    Write-Host "Training failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
