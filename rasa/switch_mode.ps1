# Switch between LLM and NLU modes for HoopMind Rasa chatbot.
# Usage: .\switch_mode.ps1 [llm|nlu]

param(
    [ValidateSet("llm", "nlu")]
    [string]$Mode
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
        Write-Host "Switched to LLM mode (Gemini + Flows)"
    }
    "nlu" {
        Copy-Item (Join-Path $ScriptDir "config_nlu.yml") $configPath -Force
        Write-Host "Switched to NLU mode (DIETClassifier + TEDPolicy)"
    }
}

Write-Host "Run 'rasa train' to retrain with the new config."
