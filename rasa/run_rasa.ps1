# run_rasa.ps1 - Unified launcher for HoopMind Rasa
#
# Usage:
#   .\run_rasa.ps1            # interactive: pick NLU or LLM
#   .\run_rasa.ps1 -Mode nlu  # offline mode (no API key)
#   .\run_rasa.ps1 -Mode llm  # Gemini + key rotation

param(
    [ValidateSet("nlu", "llm")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $ScriptDir "config.yml"

if ([string]::IsNullOrEmpty($Mode)) {
    if (Select-String -Path $configPath -Pattern "CompactLLMCommandGenerator" -Quiet) {
        $current = "llm"
    } elseif (Select-String -Path $configPath -Pattern "DIETClassifier" -Quiet) {
        $current = "nlu"
    } else {
        $current = "unknown"
    }

    Write-Host ""
    Write-Host "Current mode: $current" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Select chatbot mode:"
    Write-Host "  [1] NLU - offline DIETClassifier (no API key needed)" -ForegroundColor White
    Write-Host "  [2] LLM - Gemini-powered (requires API keys in .env)" -ForegroundColor White
    $choice = Read-Host "Choose [1/2] (default: 1)"
    $Mode = if ($choice -eq "2") { "llm" } else { "nlu" }
    Write-Host ""
}

switch ($Mode) {
    "nlu" { & "$ScriptDir\run_rasa_nlu.ps1" }
    "llm" { & "$ScriptDir\run_rasa_llm.ps1" }
}
