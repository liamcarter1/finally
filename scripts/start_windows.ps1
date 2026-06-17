<#
.SYNOPSIS
    Start the FinAlly container (Windows PowerShell). Idempotent.
.PARAMETER Build
    Force a rebuild of the image even if it already exists.
.PARAMETER NoOpen
    Do not attempt to open the browser.
.EXAMPLE
    .\scripts\start_windows.ps1
    .\scripts\start_windows.ps1 -Build
#>
[CmdletBinding()]
param(
    [switch]$Build,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$Image     = "finally:latest"
$Container = "finally"
$Volume    = "finally-data"
$Port      = 8000
$Url       = "http://localhost:$Port"

# Resolve project root (parent of this scripts/ dir) so paths work from anywhere.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
Set-Location $RootDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is not installed or not on PATH."
    exit 1
}

# Build the image if it's missing or a rebuild was requested.
$imageExists = $false
try {
    docker image inspect $Image *> $null
    if ($LASTEXITCODE -eq 0) { $imageExists = $true }
} catch { $imageExists = $false }

if ($Build -or (-not $imageExists)) {
    Write-Host "Building image $Image..."
    docker build -t $Image .
    if ($LASTEXITCODE -ne 0) { Write-Error "docker build failed."; exit 1 }
} else {
    Write-Host "Image $Image already exists (use -Build to rebuild)."
}

# Ensure a .env exists; fall back to .env.example so --env-file never fails.
$EnvFile = ".env"
if (-not (Test-Path $EnvFile)) {
    if (Test-Path ".env.example") {
        Write-Host "No .env found; copying .env.example -> .env (edit it to add your keys)."
        Copy-Item ".env.example" ".env"
    } else {
        Write-Warning "No .env or .env.example found; starting without an env file."
        $EnvFile = $null
    }
}

# Remove any existing container (running or stopped) so we pick up the latest
# image/config. The named volume is left intact.
$containerExists = $false
try {
    docker container inspect $Container *> $null
    if ($LASTEXITCODE -eq 0) { $containerExists = $true }
} catch { $containerExists = $false }

if ($containerExists) {
    Write-Host "Removing existing container $Container..."
    docker rm -f $Container *> $null
}

Write-Host "Starting container $Container..."
$runArgs = @("run", "-d", "--name", $Container, "-p", "$($Port):8000", "-v", "$($Volume):/app/db")
if ($EnvFile) { $runArgs += @("--env-file", $EnvFile) }
$runArgs += $Image
docker @runArgs *> $null
if ($LASTEXITCODE -ne 0) { Write-Error "docker run failed."; exit 1 }

Write-Host ""
Write-Host "FinAlly is starting at: $Url"
Write-Host "  Logs:  docker logs -f $Container"
Write-Host "  Stop:  .\scripts\stop_windows.ps1"

if (-not $NoOpen) {
    Start-Process $Url -ErrorAction SilentlyContinue
}
