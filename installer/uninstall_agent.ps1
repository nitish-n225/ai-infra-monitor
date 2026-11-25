<#
.SYNOPSIS
    Stops and uninstalls the Enterprise Autonomous AI Infrastructure Monitoring Agent.
#>
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\EnterpriseAIMonitorAgent",
    [switch]$KeepData
)

$ErrorActionPreference = "SilentlyContinue"
$TaskName = "EnterpriseAIMonitorAgent"

Write-Host "Stopping and removing Scheduled Task '$TaskName'..." -ForegroundColor Yellow
Stop-ScheduledTask -TaskName $TaskName
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false

$VenvPython = Join-Path $InstallDir "venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    Push-Location $InstallDir
    & $VenvPython -m agent.win_service stop 2>$null
    & $VenvPython -m agent.win_service remove 2>$null
    Pop-Location
}

if (-not $KeepData -and (Test-Path $InstallDir)) {
    Write-Host "Removing installation directory $InstallDir ..." -ForegroundColor Yellow
    Remove-Item -Path $InstallDir -Recurse -Force
}

Write-Host "Agent uninstalled cleanly." -ForegroundColor Green

