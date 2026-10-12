"""Standalone TRMNL BYOS server — stdlib only.
Reads options from env vars injected by HAOS (option key uppercased)."""

import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


options = json.loads("options.json").read_text(encoding="utf-8")

_devices = {}                     # norm_mac -> {api_key, friendly_id, registered}
_counter = 0
_lock = threading.Lock()


def norm_mac(mac: str) -> str:
    return mac.replace(":", "").replace("-", "").lower()


def get_device(mac: str) -> dict:
    k = norm_mac(mac)
    if k not in _devices:
        _devices[k] = {
            "api_key": str(uuid.uuid4()),
            "friendly_id": (k[-6:] or "DEV000").upper(),
            "registered": False,
        }
    return _devices[k]


def next_filename() -> str:
    """Unique per‑poll cache key. The firmware re‑downloads
    image_url whenever filename changes."""
    global _counter
    with _lock:
        _counter += 1
        return f"trmnl_{_counter}_{int(time.time())}.png"


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/api/setup":
            self._setup()
        elif p == "/api/display":
            self._display()
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/log":
            self._log()
        else:
            self._json(404, {"error": "not found"})

    # ---- 1. setup : MAC -> api_key (called once after WiFi) ----
    def _setup(self):
        mac = self.headers.get("ID", "")
        if not mac:
            self._json(400, {"error": "missing ID header"})
            return
        dev = get_device(mac)
        dev["registered"] = True
        self._json(200, {
            "status": 200,
            "api_key": dev["api_key"],
            "friendly_id": dev["friendly_id"],
            "image_url": options['IMAGE_BASE_URL'],          # one‑shot setup image
            "message": f"Registered as {dev['friendly_id']}",
        })

    # ---- 2. display : every wake ----
    def _display(self):
        mac = self.headers.get("ID", "")
        token = self.headers.get("Access-Token", "")
        if not mac:
            self._json(400, {"error": "missing ID header"})
            return
        dev = get_device(mac)
        if not dev["registered"]:
            self._json(202, {"status": 202})       # not registered yet
            return
        if dev["api_key"] != token:
            self._json(401, {"error": "invalid token"})
            return
        self._json(200, {
            "status": 0,
            "image_url": options['IMAGE_BASE_URL'],
            "filename": next_filename(),           # <- unique id / cache key
            "refresh_rate": options['REFRESH_RATE'],
            "reset_firmware": False,
            "update_firmware": False,
            "special_function": "identify",
        })

    # ---- 3. log : device posts errors ----
    def _log(self):
        mac = self.headers.get("ID", "")
        ln = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(ln) if ln else b"{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
        for e in data.get("logs", []):
            print(f"[log] device={norm_mac(mac)} {e.get('message','?')}", flush=True)
        self._json(200, {"status": 200})

    def _json(self, code: int, body: dict):
        d = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", options['PORT']), Handler)
    print(f"[trmnl] listening on 0.0.0.0:{options['PORT']}  image_url={options['IMAGE_BASE_URL']}", flush=True)
    srv.serve_forever()
