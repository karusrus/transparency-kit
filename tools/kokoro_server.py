#!/usr/bin/env python3
"""Tiny HTTP wrapper around Kokoro-82M (kokoro-onnx) so n8n in Docker can call it on the host.

  POST /tts   {"text": "...", "voice": "af_bella", "speed": 1.0, "lang": "en-us"}  → audio/wav
  GET  /voices                                                                    → JSON list

Run from the transparency-kit folder with the teardown-engine environment (it has kokoro-onnx and soundfile):
  ../teardown-engine/.venv/bin/python tools/kokoro_server.py --port 8880
Model files are the ones teardown-engine already uses (models/kokoro/*).
"""
import argparse, io, json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent.parent / "teardown-engine"
MODEL = ENGINE / "models/kokoro/kokoro-v1.0.int8.onnx"
VOICES = ENGINE / "models/kokoro/voices-v1.0.bin"

_k = None
def kokoro():
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(str(MODEL), str(VOICES))
    return _k


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/voices"):
            return self._send(200, json.dumps(sorted(kokoro().get_voices())).encode())
        return self._send(200, json.dumps({"ok": True, "model": "Kokoro-82M int8 (kokoro-onnx)"}).encode())

    def do_POST(self):
        if not self.path.startswith("/tts"):
            return self._send(404, b'{"error":"not found"}')
        n = int(self.headers.get("Content-Length", "0") or 0)
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
            text = str(req.get("text", "")).strip()
            if not text:
                return self._send(400, b'{"error":"text is required"}')
            t0 = time.time()
            import soundfile
            samples, rate = kokoro().create(text, voice=req.get("voice", "af_heart"),
                                            speed=float(req.get("speed", 1.0)), lang=req.get("lang", "en-us"))
            buf = io.BytesIO()
            soundfile.write(buf, samples, rate, format="WAV")
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("X-Kokoro-Seconds", f"{len(samples)/rate:.2f}")
            self.send_header("X-Kokoro-Gen-Ms", str(int((time.time() - t0) * 1000)))
            self.send_header("Content-Length", str(buf.getbuffer().nbytes))
            self.end_headers()
            self.wfile.write(buf.getvalue())
            print(f"tts voice={req.get('voice')} chars={len(text)} audio={len(samples)/rate:.1f}s gen={time.time()-t0:.1f}s", flush=True)
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"error": str(e)}).encode())

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8880); ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    if not MODEL.exists():
        sys.exit(f"model not found: {MODEL}")
    kokoro()
    print(f"kokoro server on http://{a.host}:{a.port}  model={MODEL.name}", flush=True)
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()
