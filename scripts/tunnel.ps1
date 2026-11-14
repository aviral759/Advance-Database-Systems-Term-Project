<#
.SYNOPSIS
  Start the app (token-protected) and expose it through a temporary public tunnel.
.EXAMPLE
  .\scripts\tunnel.ps1                         # cloudflared quick tunnel (no account needed)
  .\scripts\tunnel.ps1 -Provider ngrok -ReadOnly
  .\scripts\tunnel.ps1 -Provider localtunnel -Token mysecret123
#>
param(
    [ValidateSet("cloudflared", "ngrok", "localtunnel")]
    [string]$Provider = "cloudflared",
    [int]$Port = 8000,
    [string]$Token = "",
    [switch]$ReadOnly
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$cmd = @{ cloudflared = "cloudflared"; ngrok = "ngrok"; localtunnel = "npx" }[$Provider]
if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    throw "'$cmd' not found on PATH. See README section 'Temporary public hosting'."
}

if (-not $Token) {
    $chars = [char[]]"abcdefghijkmnopqrstuvwxyz23456789"
    $Token = -join (1..24 | ForEach-Object { $chars | Get-Random })
}
$env:HPS_DEMO_TOKEN = $Token
$env:HPS_READ_ONLY = $(if ($ReadOnly) { "1" } else { "0" })

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "[1/3] Starting API on http://127.0.0.1:$Port (token-protected, read-only=$($env:HPS_READ_ONLY))" -ForegroundColor Cyan
$server = Start-Process -FilePath $Python -PassThru -ArgumentList @(
    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port", "--proxy-headers")

Write-Host "[2/3] Waiting for the model and index to load..." -ForegroundColor Cyan
$deadline = (Get-Date).AddMinutes(5)
$ready = $false
while ((Get-Date) -lt $deadline) {
    if ($server.HasExited) { throw "Server exited early. Run uvicorn manually to see the error." }
    try { Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2 | Out-Null; $ready = $true; break }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) { Stop-Process -Id $server.Id -Force; throw "Server did not become healthy within 5 minutes." }

Write-Host ""
Write-Host "[3/3] Opening $Provider tunnel. When the public URL appears, open/share:" -ForegroundColor Cyan
Write-Host "      <PUBLIC_URL>/?token=$Token" -ForegroundColor Yellow
Write-Host "      Local:  http://127.0.0.1:$Port/?token=$Token"
Write-Host "      Ctrl+C stops the tunnel and the server."
Write-Host ""
try {
    switch ($Provider) {
        "cloudflared" { cloudflared tunnel --url "http://127.0.0.1:$Port" }
        "ngrok"       { ngrok http $Port }
        "localtunnel" { npx --yes localtunnel --port $Port }
    }
}
finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
    Write-Host "Tunnel and server stopped." -ForegroundColor Cyan
}