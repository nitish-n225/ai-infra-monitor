<#
.SYNOPSIS
    Installs and starts the Enterprise Autonomous AI Infrastructure Monitoring Agent on Windows 10/11.
.DESCRIPTION
    - Displays an explicit data-collection disclosure and requires affirmative user consent.
    - Installs the agent into %LOCALAPPDATA%\EnterpriseAIMonitorAgent with a dedicated Python venv.
    - Configures agent_config.json with the Central Backend URL and Enrollment Token.
    - Registers a Windows Scheduled Task so the agent starts automatically at logon with user consent.
#>
param(
    [string]$BackendUrl = "",
    [string]$EnrollmentToken = "",
    [string]$ClientOrg = "Default",
    [string]$WatchedLogs = "",
    [switch]$IncludeSecurityEvents,
    [switch]$InstallAsService,
    [switch]$AcceptConsent,
    [string]$InstallDir = "$env:LOCALAPPDATA\EnterpriseAIMonitorAgent"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host " Enterprise Autonomous AI Infrastructure Monitoring Agent - Windows Setup" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "DISCLOSURE OF MONITORED DATA:" -ForegroundColor Yellow
Write-Host "  1. Windows Event Viewer logs (System, Application, and optional Security)"
Write-Host "  2. System performance metrics (CPU, RAM, Disk, Network IO, Processes, Services)"
Write-Host "  3. Explicitly configured application log file paths"
Write-Host ""
Write-Host "PRIVACY GUARANTEE:" -ForegroundColor Green
Write-Host "  This agent does NOT read personal documents, passwords, keystrokes, or browser history."
Write-Host ""

if (-not $AcceptConsent) {
    $consentReply = Read-Host "Do you explicitly authorize installing and running this monitoring agent? Type YES to continue"
    if ($consentReply -ne "YES") {
        Write-Host "Installation cancelled because explicit consent was not granted." -ForegroundColor Red
        exit 1
    }
}

if ([string]::IsNullOrWhiteSpace($BackendUrl)) {
    $BackendUrl = Read-Host "Enter Central Backend URL (e.g. https://monitor.yourdomain.com or http://192.168.1.50:8000)"
}
$BackendUrl = $BackendUrl.Trim().TrimEnd("/")

if ($BackendUrl -match "localhost|127\.0\.0\.1") {
    Write-Warning "You entered a local loopback URL ($BackendUrl). Only use this if the Central Backend runs on THIS exact computer."
}

if ([string]::IsNullOrWhiteSpace($EnrollmentToken)) {
    $EnrollmentToken = Read-Host "Enter Enrollment Token issued by your Admin Dashboard"
}
$EnrollmentToken = $EnrollmentToken.Trim()

if ([string]::IsNullOrWhiteSpace($BackendUrl) -or [string]::IsNullOrWhiteSpace($EnrollmentToken)) {
    Write-Error "BackendUrl and EnrollmentToken are required."
    exit 1
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceAgentDir = Join-Path $RepoRoot "agent"
if (-not (Test-Path $SourceAgentDir)) {
    Write-Error "Cannot find agent source directory at $SourceAgentDir"
    exit 1
}

Write-Host "[1/5] Preparing installation directory at $InstallDir ..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$DestAgentDir = Join-Path $InstallDir "agent"
Copy-Item -Path $SourceAgentDir -Destination $InstallDir -Recurse -Force

Write-Host "[2/5] Creating isolated Python virtual environment..."
$VenvDir = Join-Path $InstallDir "venv"
if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
}
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPythonW = Join-Path $VenvDir "Scripts\pythonw.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Python virtual environment creation failed. Ensure Python 3.10+ is installed and on PATH."
    exit 1
}

Write-Host "[3/5] Installing Windows agent dependencies (psutil, pywin32, requests)..."
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $DestAgentDir "requirements-agent.txt") --quiet

Write-Host "[4/5] Writing agent_config.json..."
$WatchedArray = @()
if (-not [string]::IsNullOrWhiteSpace($WatchedLogs)) {
    $WatchedArray = $WatchedLogs.Split(";") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
}

$Channels = @("System", "Application")
if ($IncludeSecurityEvents) {
    $Channels += "Security"
}

$ConfigObj = @{
    backend_url = $BackendUrl
    enrollment_token = $EnrollmentToken
    client_org = $ClientOrg
    consent_accepted = $true
    heartbeat_interval_sec = 10
    telemetry_interval_sec = 10
    log_poll_interval_sec = 5
    event_channels = $Channels
    include_security_events = [bool]$IncludeSecurityEvents
    watched_log_paths = $WatchedArray
    initial_event_lookback = 20
}
$ConfigPath = Join-Path $InstallDir "agent_config.json"
$StatePath = Join-Path $InstallDir "agent_state.db"
$ConfigObj | ConvertTo-Json -Depth 5 | Set-Content -Path $ConfigPath -Encoding UTF8

if ($InstallAsService) {
    Write-Host "[5/5] Installing native Windows Service (EnterpriseAIMonitorService)..."
    $env:AGENT_CONFIG_PATH = $ConfigPath
    $env:AGENT_STATE_PATH = $StatePath
    Push-Location $InstallDir
    & $VenvPython -m agent.win_service --startup auto install
    & $VenvPython -m agent.win_service start
    Pop-Location
    Write-Host "Windows Service 'EnterpriseAIMonitorService' installed and started!" -ForegroundColor Green
} else {
    Write-Host "[5/5] Registering Windows Scheduled Task for automatic startup..."
    $TaskName = "EnterpriseAIMonitorAgent"
    $RunnerExe = if (Test-Path $VenvPythonW) { $VenvPythonW } else { $VenvPython }
    $Arguments = "-m agent.main --config `"$ConfigPath`" --state `"$StatePath`""

    $Action = New-ScheduledTaskAction -Execute $RunnerExe -Argument $Arguments -WorkingDirectory $InstallDir
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 365)

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Enterprise Autonomous AI Infrastructure Monitoring Agent" -Force | Out-Null
    Start-ScheduledTask -TaskName $TaskName
}

Write-Host ""
Write-Host "Installation complete! The monitoring agent is now running in the background." -ForegroundColor Green
Write-Host "  Install Path : $InstallDir"
Write-Host "  Task Name    : $TaskName"
Write-Host "  Config File  : $ConfigPath"
Write-Host "  To Uninstall : Run .\installer\uninstall_agent.ps1"

