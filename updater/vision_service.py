import argparse
import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np


class State:
    running = True
    camera_on = False
    motion = False
    level = 0.0
    last_motion = 0.0
    error = ""
    lock = threading.Lock()


def camera_loop():
    capture = None
    try:
        capture = cv2.VideoCapture(0)
        if not capture.isOpened():
            with State.lock:
                State.error = "Kamera açılamadı"
            return
        with State.lock:
            State.camera_on = True
            State.error = ""
        previous = None
        while State.running:
            ok, frame = capture.read()
            if not ok:
                time.sleep(0.2)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            if previous is None:
                previous = gray
                continue
            diff = cv2.absdiff(previous, gray)
            mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            ratio = float(np.count_nonzero(mask)) / 255.0 / float(gray.shape[0] * gray.shape[1])
            now = time.time()
            with State.lock:
                State.level = round(ratio, 5)
                if ratio > 0.01:
                    State.motion = True
                    State.last_motion = now
                elif now - State.last_motion > 1.5:
                    State.motion = False
            previous = gray
            time.sleep(0.03)
    except Exception as exc:
        with State.lock:
            State.error = str(exc)
    finally:
        if capture is not None:
            capture.release()
        with State.lock:
            State.camera_on = False


def start_camera():
    if State.camera_on:
        return
    State.running = True
    threading.Thread(target=camera_loop, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json({})

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/status":
            with State.lock:
                self.send_json({
                    "camera": State.camera_on,
                    "motion": State.motion,
                    "level": State.level,
                    "error": State.error,
                })
        elif path == "/ping":
            self.send_json({"ok": True})
        else:
            self.send_json({"error": "bulunamadı"}, 404)

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/start":
            start_camera()
            self.send_json({"started": True})
        elif path == "/stop":
            State.running = False
            self.send_json({"stopped": True})
        else:
            self.send_json({"error": "bulunamadı"}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", action="store_true")
    args = parser.parse_args()
    if not args.service:
        start_camera()
        time.sleep(1)
        print(json.dumps({"camera": State.camera_on, "error": State.error}, ensure_ascii=False))
        return 0
    start_camera()
    server = ThreadingHTTPServer(("127.0.0.1", 8780), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
