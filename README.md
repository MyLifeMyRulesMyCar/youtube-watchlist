# YouTube Weekend Watchlist

Scans a list of YouTube channels every weekend, detects videos published in the
last 7 days, writes a report, and auto-plays them in your browser.

- **No API key, no cookies, no third-party services** — uses public YouTube RSS
  feeds for the scan and the YouTube IFrame player (your normal browser session)
  for playback.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Add your channels

Edit `channels.yml`:

```yaml
channels:
  - name: Fireship
    url: https://www.youtube.com/@Fireship
  - name: MReflow
    url: https://www.youtube.com/@mreflow/
```

Supported URL formats: `@handle`, `/channel/UC...`, `/c/name`, `/user/name`.

## Manual run

```powershell
# Scan for new videos (last 7 days) and auto-play them in the browser
.\.venv\Scripts\python.exe watch.py --reset

# Scan only, no playback
.\.venv\Scripts\python.exe watch.py --reset --no-play

# Replay the latest report without re-scanning
.\.venv\Scripts\python.exe player.py

# Play a specific report
.\.venv\Scripts\python.exe player.py --file reports\new_videos_2026-08-16.json
```

Player controls: `Space` = pause, `N` = next, `P` = previous, `Q` = close.

## Automation (Windows Task Scheduler)

Run `setup_task.ps1` once to register a scheduled task that runs every Sunday at
9:00 AM. It scans, writes the report, auto-opens the browser player, and
commits + pushes the weekly report to git.
