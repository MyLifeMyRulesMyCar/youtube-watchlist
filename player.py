import argparse
import http.server
import json
import os
import socket
import sys
import threading
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
PLAYER_HTML = os.path.join(BASE_DIR, "player.html")


def find_latest_report():
    if not os.path.isdir(REPORTS_DIR):
        return None
    files = [
        f
        for f in os.listdir(REPORTS_DIR)
        if f.startswith("new_videos_") and f.endswith(".json")
    ]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(REPORTS_DIR, files[0])


def build_html(videos, origin):
    vids_json = json.dumps(videos)
    origin_json = json.dumps(origin)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>YouTube Watchlist Player</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; background: #0f0f0f; color: #eee; }
  .wrap { display: flex; gap: 20px; align-items: flex-start; max-width: 1200px; }
  .main { flex: 1; }
  #player { width: 100%; max-width: 854px; aspect-ratio: 16/9; background: #000; }
  #info { margin: 10px 0; font-size: 16px; color: #ccc; }
  #info .channel { color: #f00; font-weight: bold; margin-right: 8px; }
  .controls { margin: 10px 0; }
  .controls button { padding: 8px 16px; margin-right: 8px; cursor: pointer; }
  .hint { color: #888; font-size: 12px; margin-top: 8px; }
  .sidebar { width: 320px; max-height: 80vh; overflow-y: auto; }
  .sidebar h3 { margin-top: 0; }
  .sidebar ul { list-style: none; padding: 0; margin: 0; }
  .sidebar li { padding: 8px; margin-bottom: 4px; background: #1a1a1a; border-radius: 4px;
                cursor: pointer; font-size: 13px; }
  .sidebar li.active { background: #c00; }
  .sidebar li .ch { color: #888; font-size: 11px; display: block; }
</style>
</head>
<body>
<div class="wrap">
  <div class="main">
    <div id="player"></div>
    <div id="info"></div>
    <div class="controls">
      <button onclick="prev()">Prev (P)</button>
      <button onclick="togglePlay()">Play / Pause (Space)</button>
      <button onclick="next()">Next (N)</button>
      <button onclick="quit()">Close (Q)</button>
    </div>
    <div class="hint">Keyboard: Space = play/pause &nbsp;|&nbsp; N = next &nbsp;|&nbsp; P = previous &nbsp;|&nbsp; Q = close</div>
  </div>
  <div class="sidebar">
    <h3>Playlist</h3>
    <ul id="list"></ul>
  </div>
</div>

<script>
var VIDEOS = __VIDEOS__;
var ORIGIN = __ORIGIN__;
var index = 0;
var player = null;

function onYouTubeIframeAPIReady() {
  player = new YT.Player("player", {
    height: "480",
    width: "854",
    videoId: VIDEOS.length ? VIDEOS[0].url.split("v=")[1] : null,
    playerVars: { autoplay: 1, rel: 0, origin: ORIGIN },
    events: { onStateChange: onStateChange }
  });
  buildList();
  update();
}

function buildList() {
  var list = document.getElementById("list");
  VIDEOS.forEach(function (v, i) {
    var li = document.createElement("li");
    li.setAttribute("data-i", i);
    var ch = document.createElement("span");
    ch.className = "ch";
    ch.textContent = v.channel;
    li.appendChild(ch);
    li.appendChild(document.createTextNode(v.title));
    li.onclick = function () { play(i); };
    list.appendChild(li);
  });
}

function update() {
  var v = VIDEOS[index];
  document.getElementById("info").innerHTML =
    '<span class="channel">' + v.channel + '</span>' + v.title;
  var items = document.querySelectorAll("#list li");
  items.forEach(function (li, i) {
    li.className = i === index ? "active" : "";
  });
}

function play(i) {
  index = (i + VIDEOS.length) % VIDEOS.length;
  var id = VIDEOS[index].url.split("v=")[1];
  player.loadVideoById(id);
  update();
}

function next() { play(index + 1); }
function prev() { play(index - 1); }

function togglePlay() {
  if (!player) return;
  if (player.getPlayerState() === 1) player.pauseVideo();
  else player.playVideo();
}

function onStateChange(e) {
  if (e.data === YT.PlayerState.ENDED) next();
}

function quit() {
  try { fetch("/quit"); } catch (err) {}
  document.body.innerHTML = "<h2 style='padding:40px'>Session ended. You can close this tab.</h2>";
}

document.addEventListener("keydown", function (e) {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  if (e.code === "Space") { e.preventDefault(); togglePlay(); }
  else if (e.code === "KeyN") { next(); }
  else if (e.code === "KeyP") { prev(); }
  else if (e.code === "KeyQ") { quit(); }
});
</script>
<script src="https://www.youtube.com/iframe_api"></script>
</body>
</html>
""".replace("__VIDEOS__", vids_json).replace("__ORIGIN__", origin_json)


class PlayerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/quit"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b"bye")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        super().do_GET()

    def log_message(self, *args):
        pass


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def play_browser(videos):
    port = free_port()
    origin = f"http://127.0.0.1:{port}"

    with open(PLAYER_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(videos, origin))

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), PlayerHandler)

    url = f"{origin}/player.html"
    print(f"Opening {len(videos)} new video(s) in your browser...")
    print(f"URL: {url}")
    print("Controls: Space=pause  N=next  P=prev  Q=close")
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="Play new YouTube videos in the browser.")
    parser.add_argument("--file", help="Path to a new_videos_*.json file")
    args = parser.parse_args()

    path = args.file or find_latest_report()
    if not path or not os.path.exists(path):
        print("No new-videos report found.")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    videos = data.get("videos", [])
    if not videos:
        print("No videos to play.")
        return

    play_browser(videos)


if __name__ == "__main__":
    main()
