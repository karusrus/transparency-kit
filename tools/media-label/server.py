#!/usr/bin/env python3
"""Optional media-label service: burns the disclosure label into video and audio metadata with ffmpeg, so the n8n
workflow itself needs no shell. n8n Cloud cannot run ffmpeg; a self-hosted n8n calls this over HTTP. If the service
is down the kit records "disclosure at publication" instead of a burnt-in label and says so on the audit view.

  POST /label?type=video|audio|image&text=<label>&small=0|1&comment=<metadata>   body = the file bytes
  → the labelled file bytes (same container format), or 4xx/5xx with a JSON error

Runs as its own container (tools/media-label/Dockerfile), started by reload.sh: http://kit-media-label:8881/label
"""
import argparse, json, shutil, subprocess, tempfile, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FONT = next((p for p in [Path("/usr/share/fonts/DejaVuSans.ttf"), Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
                         Path("/Library/Fonts/Arial.ttf")] if p.exists()), None)
EXT = {"video": ".mp4", "audio": ".wav", "image": ".png"}


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._json(200, {"ok": True, "ffmpeg": bool(shutil.which("ffmpeg")), "font": str(FONT)})

    def do_POST(self):
        if not self.path.startswith("/label"):
            return self._json(404, {"error": "not found"})
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        kind = (q.get("type") or ["video"])[0]
        text = (q.get("text") or ["AI-generated - EU AI Act Art. 50"])[0]
        small = (q.get("small") or ["0"])[0] == "1"
        comment = (q.get("comment") or [text])[0]
        ext = (q.get("ext") or [EXT.get(kind, ".bin")])[0]
        n = int(self.headers.get("Content-Length", "0") or 0)
        data = self.rfile.read(n)
        if not data:
            return self._json(400, {"error": "empty body"})
        safe = "".join(ch for ch in text if ch.isalnum() or ch in " .,-()")[:120]
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / ("in" + ext), Path(d) / ("out" + ext)
            src.write_bytes(data)
            if kind == "audio":
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c", "copy", "-metadata", f"comment={comment}", str(dst)]
            else:
                if not FONT:
                    return self._json(500, {"error": "no font for drawtext"})
                draw = (f"drawtext=fontfile={FONT}:text='{safe}':fontcolor=white@0.85:fontsize=h/48:box=1:boxcolor=black@0.35:boxborderw=6:x=w-tw-14:y=h-th-14"
                        if small else
                        f"drawtext=fontfile={FONT}:text='{safe}':fontcolor=white:fontsize=h/28:box=1:boxcolor=black@0.55:boxborderw=10:x=20:y=h-th-20")
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", draw] + (["-c:a", "copy"] if kind == "video" else []) + ["-metadata", f"comment={comment}", str(dst)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0 or not dst.exists():
                return self._json(500, {"error": r.stderr[-400:]})
            out = dst.read_bytes()
        self.send_response(200); self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
        print(f"label {kind} {len(data)}B -> {len(out)}B small={small}", flush=True)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8881); ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    print(f"media-label server on http://{a.host}:{a.port}  ffmpeg={shutil.which('ffmpeg')}  font={FONT}", flush=True)
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()
