<#
.SYNOPSIS
    Stop and remove the FinAlly container (Windows PowerShell). Idempotent.
    Does NOT remove the named volume, so the SQLite database persists.
.EXAMPLE
    .\scripts\stop_windows.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$Container = "finally"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is not installed or not on PATH."
    exit 1
}

$containerExists = $false
try {
    docker container inspect $Container *> $null
    if ($LASTEXITCODE -eq 0) { $containerExists = $true }
} catch { $containerExists = $false }

if ($containerExists) {
    Write-Host "Stopping and removing container $Container..."
    docker rm -f $Container *> $null
    Write-Host "Done. The 'finally-data' volume was preserved (your data is safe)."
} else {
    Write-Host "Container $Container is not present; nothing to stop."
}
