# YouTube Weekend Watchlist

Scans a list of YouTube channels every week, detects videos published in the
last 7 days, writes a report, and publishes a browser playlist via GitHub Pages.

- Uses public YouTube RSS feeds (no API key) — the scan runs on your own
  machine, so it isn't blocked the way GitHub's server IPs are. Playback uses
  the YouTube IFrame player.

## How it works

A Windows Scheduled Task (**"YouTube Watchlist Weekly Scan"**) runs
`run_weekly.ps1` every Sunday at 08:30 PM. It:

1. Fetches each channel's latest uploads from the public RSS feed.
2. Detects videos published in the last 7 days that are not already in a
   committed report.
3. Writes `reports/new_videos_<date>.md` and regenerates `docs/index.html`.
4. Commits and pushes — GitHub Pages rebuilds the player automatically.

Open the player at:

```
https://mylifemyrulesmycar.github.io/youtube-watchlist/
```

## Setup

1. Edit `channels.yml` to list your channels:

   ```yaml
   channels:
     - name: Fireship
       url: https://www.youtube.com/@Fireship
       playlist: AI
   ```

   Supported URL formats: `@handle`, `/channel/UC...`, `/c/name`, `/user/name`.

   Channels are grouped into tabs in the player by `playlist` (videos without
   one fall back to a `General` tab).

2. Enable auto-push (one-time, ~5 min). The task pushes over SSH using a
   passphrase-less deploy key:

   - On GitHub: repo **Settings → Deploy keys → Add deploy key**, paste the
     public key from `~/.ssh/id_ed25519_deploy.pub`, give it a title, and check
     **Allow write access**.
   - Verify it works: `ssh -T git@github-deploy` (you should see `Hi <user>!`).

3. Enable GitHub Pages: repo **Settings → Pages → Source: Deploy from a branch
   → Branch: main, folder `/docs`**.

4. The scheduled task is registered already (every Sunday 08:30 PM, runs when
   you are logged in). To re-create it after moving the repo, run:

   ```powershell
   Register-ScheduledTask -TaskName "YouTube Watchlist Weekly Scan" `
     -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "08:30PM") `
     -Action (New-ScheduledTaskAction -Execute "powershell.exe" `
       -Argument "-NoProfile -ExecutionPolicy Bypass -File `"D:\watchlist\run_weekly.ps1`"")
   ```

## Adding a new channel

When you add a new `@handle` channel, the scan resolves its channel ID and
commits it to `channel_ids.json`. If resolution fails, use a `/channel/UC...`
URL instead, or resolve it once locally and commit. Add a `playlist:` line to
place the channel in a specific player tab (e.g. `AI` or `Hardware`).

## Running manually

```powershell
.\.venv\Scripts\python.exe watch.py                    # scan + play in browser
.\.venv\Scripts\python.exe watch.py --no-play --git-sync  # scan + push now
powershell -File .\run_weekly.ps1                      # same as the scheduled task
```

Player controls: `Space` = pause, `N` = next, `P` = previous, `Q` = close.
