# Starts the API and web app for local development (Windows PowerShell).
# Usage: ./scripts/dev.ps1 [-ApiPort 8000] [-WebPort 3000]
param([int]$ApiPort = 8000, [int]$WebPort = 3000)

$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "apps/api"
$web = Join-Path $root "apps/web"

if (-not (Test-Path (Join-Path $api ".venv"))) {
  Write-Host "Creating Python virtualenv and installing API dependencies..."
  python -m venv (Join-Path $api ".venv")
  & (Join-Path $api ".venv/Scripts/pip") install -r (Join-Path $api "requirements-dev.txt")
}
if (-not (Test-Path (Join-Path $web "node_modules"))) {
  Write-Host "Installing web dependencies..."
  Push-Location $web; npm install; Pop-Location
}

Start-Process -NoNewWindow -FilePath (Join-Path $api ".venv/Scripts/python") -ArgumentList "-m uvicorn app.main:app --reload --port $ApiPort" -WorkingDirectory $api
$env:API_URL = "http://127.0.0.1:$ApiPort"
Push-Location $web
npx next dev --webpack -p $WebPort
Pop-Location
