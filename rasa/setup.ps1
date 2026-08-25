# setup.ps1 - First-time setup for HoopMind Rasa
#
# Usage: .\setup.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Setting up HoopMind Rasa..." -ForegroundColor Cyan

# Create venv + install exact locked dependencies (Python 3.11 per pyproject.toml)
Write-Host "Syncing environment from uv.lock..." -ForegroundColor Yellow
Push-Location $ScriptDir
try {
    & uv sync
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Create .env if missing
$envPath = Join-Path $ScriptDir ".env"
if (!(Test-Path $envPath)) {
    Write-Host "Creating .env template..." -ForegroundColor Yellow
    @"
# Rasa Pro license (from https://app.rasa.com/)
RASA_LICENSE=your-license-here

# Gemini API keys (get from https://aistudio.google.com/apikey)
GEMINI_API_KEY=your-primary-key-here
GEMINI_API_KEY_1=your-second-key-here
GEMINI_API_KEY_2=your-third-key-here
GEMINI_API_KEY_3=your-fourth-key-here

# Model
GEMINI_MODEL=gemini-2.0-flash
"@ | Set-Content $envPath
    Write-Host "Created .env - fill in your API keys before running" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit .env with your API keys"
Write-Host "  2. .\run_rasa_llm.ps1"
