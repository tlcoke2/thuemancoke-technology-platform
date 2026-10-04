$ErrorActionPreference = "Stop"

Write-Host "Checking production site..." -ForegroundColor Cyan

$api = Invoke-RestMethod -Uri "https://api.thuemancokelimited.com/api/health"
if (-not $api.ok) { throw "API health check failed" }

$web = Invoke-WebRequest -Uri "https://thuemancokelimited.com" -UseBasicParsing
if ($web.StatusCode -ne 200) { throw "Website check failed" }

Write-Host "API and website are responding successfully." -ForegroundColor Green
