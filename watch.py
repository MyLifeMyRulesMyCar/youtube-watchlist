import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests
import yaml

import git_sync
import player

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "channels.yml")
CHANNEL_IDS_FILE = os.path.join(BASE_DIR, "channel_ids.json")
SEEN_FILE = os.path.join(BASE_DIR, "seen.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

ATOM_NS = "http://www.w3.org/2005/Atom"
YT_NS = "http://www.youtube.com/xml/schemas/2015"

CHANNEL_ID_RE = re.compile(r"UC[0-9A-Za-z_-]{22}")

CHANNEL_ID_PATTERNS = [
    re.compile(r'<link rel="canonical" href="[^"]*channel/(UC[0-9A-Za-z_-]{22})'),
    re.compile(r'<meta itemprop="identifier" content="(UC[0-9A-Za-z_-]{22})'),
    re.compile(r'<meta itemprop="channelId" content="(UC[0-9A-Za-z_-]{22})'),
    re.compile(r'"channelId":"(UC[0-9A-Za-z_-]{22})'),
    re.compile(r'<meta property="og:url" content="[^"]*channel/(UC[0-9A-Za-z_-]{22})'),
    re.compile(r'"externalId":"(UC[0-9A-Za-z_-]{22})'),
]


def load_json(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("channels", [])


def extract_direct_channel_id(url):
    m = re.search(r"/channel/(UC[0-9A-Za-z_-]{22})", url)
    if m:
        return m.group(1)
    m = CHANNEL_ID_RE.search(url)
    return m.group(0) if m else None


def resolve_channel_id(url, name):
    channel_ids = load_json(CHANNEL_IDS_FILE)
    if url in channel_ids:
        return channel_ids[url]

    direct = extract_direct_channel_id(url)
    if direct:
        channel_ids[url] = direct
        save_json(CHANNEL_IDS_FILE, channel_ids)
        return direct

    resp = requests.get(
        url,
        headers={**HEADERS, "Cookie": "CONSENT=YES+cb.20220301-00-p0.en+FX+xyz"},
        timeout=30,
    )
    resp.raise_for_status()
    html = resp.text
    for pattern in CHANNEL_ID_PATTERNS:
        m = pattern.search(html)
        if m:
            channel_ids[url] = m.group(1)
            save_json(CHANNEL_IDS_FILE, channel_ids)
            return m.group(1)

    print(f"WARNING: could not resolve channel id for '{name}' ({url})")
    return None


def get_videos(channel_id):
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    resp = requests.get(feed_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    videos = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        video_id = entry.findtext(f"{{{YT_NS}}}videoId")
        title = entry.findtext(f"{{{ATOM_NS}}}title")
        published = entry.findtext(f"{{{ATOM_NS}}}published")
        if not video_id or not title:
            continue
        published_date = ""
        if published:
            try:
                published_date = datetime.fromisoformat(
                    published.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d")
            except ValueError:
                published_date = published
        videos.append(
            {
                "id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": published_date,
            }
        )
    return videos


def write_report(new_videos, report_date):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    md_path = os.path.join(REPORTS_DIR, f"new_videos_{report_date}.md")
    json_path = os.path.join(REPORTS_DIR, f"new_videos_{report_date}.json")

    lines = [f"# New Videos - {report_date}", ""]
    for channel, vids in new_videos.items():
        lines.append(f"## {channel}")
        for v in vids:
            lines.append(f"- [{v['title']}]({v['url']}) ({v['published']})")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    flat = [
        {
            "channel": channel,
            "title": v["title"],
            "url": v["url"],
            "published": v["published"],
        }
        for channel, vids in new_videos.items()
        for v in vids
    ]
    save_json(json_path, {"date": report_date, "videos": flat})

    return md_path, json_path, flat


def main():
    parser = argparse.ArgumentParser(description="Scan YouTube channels for new videos.")
    parser.add_argument("--no-play", action="store_true", help="Do not launch the player")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Only report videos published within the last N days (default 7)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear tracking history and re-detect the current window as new",
    )
    parser.add_argument(
        "--git-sync",
        action="store_true",
        help="Commit and push the weekly report to git after the run",
    )
    args = parser.parse_args()

    channels = load_config()
    if not channels:
        print("No channels found in channels.yml")
        sys.exit(1)

    if args.reset:
        seen = {}
        is_baseline = False
    else:
        seen = load_json(SEEN_FILE)
        is_baseline = not seen

    cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    all_new = {}
    total_new = 0

    for ch in channels:
        name = ch.get("name") or ch.get("url")
        url = ch.get("url")
        if not url:
            print(f"WARNING: channel '{name}' has no url, skipping")
            continue

        channel_id = resolve_channel_id(url, name)
        if not channel_id:
            continue

        try:
            videos = get_videos(channel_id)
        except Exception as e:
            print(f"WARNING: failed to fetch videos for '{name}': {e}")
            continue

        current_ids = [v["id"] for v in videos]
        known = set(seen.get(url, []))

        in_window = [v for v in videos if v["published"] and v["published"] >= cutoff]

        if is_baseline:
            new_vids = []
        else:
            new_vids = [v for v in in_window if v["id"] not in known]

        seen[url] = current_ids

        if new_vids:
            all_new[name] = new_vids
            total_new += len(new_vids)
            print(f"{name}: {len(new_vids)} new video(s)")

    save_json(SEEN_FILE, seen)

    report_date = datetime.now().strftime("%Y-%m-%d")

    if is_baseline:
        print(
            "Baseline established - recorded current videos. "
            "No new videos reported this first run."
        )
        return

    if not all_new:
        print("No new videos this week.")
        return

    md_path, json_path, flat = write_report(all_new, report_date)
    print(f"Report written to {md_path}")

    player.generate_pages(flat)

    if not args.no_play:
        player_path = os.path.join(BASE_DIR, "player.py")
        print("Launching player...")
        subprocess.run([sys.executable, player_path, "--file", json_path])

    if args.git_sync:
        git_sync.run()


if __name__ == "__main__":
    main()
