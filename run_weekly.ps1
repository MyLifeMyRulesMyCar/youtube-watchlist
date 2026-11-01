# Weekly YouTube watchlist scan + auto-push.
# Run by Windows Task Scheduler every Sunday (see README "Automation").
$ErrorActionPreference = "Continue"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repo

$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $py) {
    return
}

$log = Join-Path $repo "weekly_scan.log"
"===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" | Out-File -FilePath $log -Append -Encoding utf8

& $py "watch.py" --no-play --git-sync *>&1 | Out-File -FilePath $log -Append -Encoding utf8

"exit code: $LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
