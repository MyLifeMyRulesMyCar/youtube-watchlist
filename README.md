# YouTube Weekend Watchlist

Scans a list of YouTube channels every week, detects videos published in the
last 7 days, writes a report, and publishes a browser playlist via GitHub Pages.

- **No API key, no cookies, no third-party services** — uses public YouTube RSS
  feeds for the scan and the YouTube IFrame player for playback.

## How it works

A GitHub Actions workflow (`.github/workflows/weekly.yml`) runs every Sunday at
09:00 (UTC+8):

1. Fetches each channel's RSS feed.
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

2. Enable GitHub Pages: repo **Settings → Pages → Source: Deploy from a branch
   → Branch: main, folder `/docs`**.

3. Push your changes — the workflow runs automatically every Sunday (or trigger
   it manually from the **Actions** tab → **Weekly scan → Run workflow**).

## Adding a new channel

When you add a new `@handle` channel, the workflow resolves its channel ID and
commits it to `channel_ids.json`. If resolution fails from GitHub's IPs, use a
`/channel/UC...` URL instead, or resolve it once locally and commit. Add a
`playlist:` line to place the channel in a specific player tab (e.g. `AI` or
`Hardware`).

## Running locally (optional)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe watch.py        # scan + play in browser
.\.venv\Scripts\python.exe watch.py --no-play
.\.venv\Scripts\python.exe player.py       # replay latest report
```

Player controls: `Space` = pause, `N` = next, `P` = previous, `Q` = close.
