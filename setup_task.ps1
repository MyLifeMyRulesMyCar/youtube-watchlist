$ErrorActionPreference = "Stop"

$taskName = "YouTubeWeekendWatchlist"
$workDir = $PSScriptRoot
$python = Join-Path $workDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment not found. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

$action = New-ScheduledTaskAction -Execute $python -Argument "watch.py --git-sync" -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9:00AM
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description "Weekly scan for new YouTube videos and play them in the browser" -Force

Write-Output "Scheduled task '$taskName' registered to run Sundays at 9:00 AM."
Write-Output "Run '$python $workDir\watch.py --reset --no-play' to test the scan now."
