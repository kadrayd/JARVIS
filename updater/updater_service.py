import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil

REPO = "kadrayd/JARVIS"
BRANCH = "main"
MANIFEST_URL = "https://raw.githubusercontent.com/kadrayd/JARVIS/main/updates.json?raw=1"
API_URL = "https://api.github.com/repos/kadrayd/JARVIS/contents/updates.json?ref=main"
ALLOWED_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "api.github.com",
    "objects.githubusercontent.com",
}
USER_AGENT = "JARVIS-Updater/3.2"
PORTS = tuple(range(8765, 8775))
VERSION_FILE = "version.json"
CACHE_SECONDS = 60


def version_tuple(value):
    parts = str(value).lstrip("v").split(".")
    out = []
    for part in parts:
        match = re.match(r"\d+", part.strip())
        out.append(int(match.group()) if match else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


def safe_url(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    split = urllib.parse.urlsplit(url)
    host = (split.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return False
    path = split.path.lower()
    return path.startswith("/kadrayd/jarvis/") or path.startswith("/repos/kadrayd/jarvis/contents/")


def safe_host(url):
    return (urllib.parse.urlsplit(url).hostname or "").lower() in ALLOWED_HOSTS


def fetch(url, timeout=20):
    if not safe_url(url):
        raise ValueError("Güvenli olmayan adres")
    context = ssl.create_default_context()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.read(), response.geturl()


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Geçersiz manifest")
    if not manifest.get("version"):
        raise ValueError("Sürüm eksik")
    url = str(manifest.get("url", ""))
    if not safe_url(url) or not url.lower().endswith(".zip"):
        raise ValueError("Geçersiz indirme adresi")
    digest = str(manifest.get("sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Geçersiz SHA-256")


def load_manifest(force=False):
    now = time.time()
    if not force and State.manifest_cache and now - State.manifest_time < CACHE_SECONDS:
        return State.manifest_cache
    errors = []
    for url in (MANIFEST_URL, API_URL):
        try:
            data, final = fetch(url)
            if not safe_host(final):
                raise ValueError("Yönlendirme güvenli değil")
            if "api.github.com" in urllib.parse.urlsplit(final).hostname:
                payload = json.loads(data.decode("utf-8"))
                data = base64.b64decode(payload["content"])
            manifest = json.loads(data.decode("utf-8"))
            validate_manifest(manifest)
            State.manifest_cache = manifest
            State.manifest_time = now
            return manifest
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("; ".join(errors))


def load_current(app_dir):
    try:
        return str(json.loads((app_dir / VERSION_FILE).read_text(encoding="utf-8"))["version"])
    except Exception:
        return "0.0.0"


def write_current(target, version):
    (target / VERSION_FILE).write_text(
        json.dumps({"version": version}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def set_progress(percent, message, done=False, success=False, error=""):
    with State.lock:
        State.progress = {
            "percent": int(percent),
            "message": str(message),
            "done": bool(done),
            "success": bool(success),
            "error": str(error),
        }


def refresh(force=False):
    try:
        manifest = load_manifest(force)
        latest = str(manifest["version"])
        State.status = {
            "ok": True,
            "current": State.current,
            "latest": latest,
            "available": version_tuple(latest) > version_tuple(State.current),
            "notes": str(manifest.get("notes", "")),
            "error": "",
        }
    except Exception as exc:
        State.status = {
            "ok": False,
            "current": State.current,
            "latest": "",
            "available": False,
            "notes": "",
            "error": str(exc),
        }


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, destination):
    if not safe_url(url):
        raise ValueError("Güvenli olmayan indirme adresi")
    context = ssl.create_default_context()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        if not safe_host(response.geturl()):
            raise ValueError("Yönlendirme güvenli değil")
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with open(destination, "wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if total:
                    ratio = min(70, 5 + int(60 * done / total))
                    set_progress(ratio, "İndiriliyor… %" + str(int(100 * done / total)))


def safe_extract(archive, target):
    target = target.resolve()
    with archive as zipped:
        for member in zipped.infolist():
            destination = (target / member.filename).resolve()
            if target not in destination.parents and destination != target:
                raise ValueError("Geçersiz zip içeriği")
        zipped.extractall(target)


def app_root(folder):
    files = list(folder.iterdir())
    executables = [p for p in files if p.is_file() and p.suffix.lower() == ".exe"]
    if executables or not files:
        return folder
    if len(files) == 1 and files[0].is_dir():
        return files[0]
    return folder


def next_target(version):
    desktop = Path.home() / "Desktop"
    name = "JARVIS " + version
    candidate = desktop / name
    index = 2
    while candidate.exists() and candidate.resolve() != State.app_dir.resolve():
        candidate = desktop / ("JARVIS " + version + " (" + str(index) + ")")
        index += 1
    return candidate


def prepare_target(target, version):
    write_current(target, version)
    for name in ("setup.exe", "JARVISUpdater.exe"):
        if not (target / name).exists():
            source = State.app_dir / name
            if source.exists():
                shutil.copy2(source, target / name)


def process_alive(path):
    path = str(path).lower()
    for process in psutil.process_iter(["exe"]):
        try:
            if process.info["exe"] and process.info["exe"].lower() == path:
                return True
        except Exception:
            pass
    return False


def launch(target):
    setup = target / "setup.exe"
    executable = setup if setup.exists() else next(target.glob("JARVIS *.exe"), None)
    if executable is None:
        raise RuntimeError("Başlatılacak exe bulunamadı")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [str(executable)],
        cwd=str(target),
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_start(target, seconds):
    marker = target / "launch-ok.flag"
    deadline = time.time() + seconds
    while time.time() < deadline:
        if marker.exists():
            return True
        time.sleep(0.5)
    return False


def kill_old(app_dir):
    root = app_dir.resolve()
    targets = []
    for process in psutil.process_iter(["pid", "exe"]):
        try:
            if not process.info["exe"] or process.pid == os.getpid():
                continue
            executable = Path(process.info["exe"]).resolve()
            if root in executable.parents and re.match(r"^JARVIS .*\.exe$", executable.name, re.I):
                targets.append(process)
        except Exception:
            pass
    for process in targets:
        try:
            process.terminate()
        except Exception:
            pass
    deadline = time.time() + 10
    while time.time() < deadline:
        if not any(process.is_running() for process in targets):
            return
        time.sleep(0.3)
    for process in targets:
        try:
            process.kill()
        except Exception:
            pass


def remove_tree(path):
    for _ in range(5):
        try:
            shutil.rmtree(path)
            return
        except Exception:
            time.sleep(0.5)


def cleanup(old_dir, new_dir):
    desktop = Path.home() / "Desktop"
    try:
        entries = list(desktop.iterdir())
    except Exception:
        entries = []
    for item in entries:
        try:
            if item.resolve() == new_dir.resolve():
                continue
            if item.is_dir() and item.name.lower().startswith("jarvis"):
                if next(item.glob("JARVIS *.exe"), None) is not None:
                    remove_tree(item)
            elif item.is_file() and re.match(r"^JARVIS.*\.exe$", item.name, re.I):
                item.unlink()
        except Exception:
            pass
    if old_dir.exists() and old_dir.resolve() != new_dir.resolve():
        remove_tree(old_dir)


def install_worker():
    temp_folder = None
    try:
        with State.lock:
            if State.installing:
                return
            State.installing = True
        set_progress(2, "Güncelleme kontrol ediliyor…")
        manifest = load_manifest(True)
        latest = str(manifest["version"])
        if version_tuple(latest) <= version_tuple(State.current):
            set_progress(100, "Zaten güncel sürüm.", done=True, success=True)
            return
        temp_folder = Path(tempfile.mkdtemp(prefix="jarvis-update-"))
        archive = temp_folder / "update.zip"
        download(manifest["url"], archive)
        set_progress(68, "Doğrulanıyor…")
        if sha256_file(archive) != str(manifest["sha256"]).lower():
            raise RuntimeError("İndirilen dosyanın SHA-256 değeri uyuşmuyor")
        set_progress(75, "Çıkarılıyor…")
        extracted = temp_folder / "new"
        with zipfile.ZipFile(archive) as zipped:
            safe_extract(zipped, extracted)
        source = app_root(extracted)
        target = next_target(latest)
        set_progress(82, "Yeni klasör oluşturuluyor…")
        shutil.move(str(source), str(target))
        prepare_target(target, latest)
        set_progress(88, "Yeni sürüm başlatılıyor…")
        launch(target)
        if not wait_start(target, 40):
            raise RuntimeError("Yeni sürüm başlamadı")
        set_progress(94, "Eski sürüm kaldırılıyor…")
        kill_old(State.app_dir)
        cleanup(State.app_dir, target)
        State.current = latest
        State.manifest_cache = None
        State.manifest_time = 0
        set_progress(100, "Güncelleme tamamlandı.", done=True, success=True)
    except Exception as exc:
        set_progress(100, "Güncelleme başarısız.", done=True, success=False, error=str(exc))
    finally:
        with State.lock:
            State.installing = False
        if temp_folder and temp_folder.exists():
            shutil.rmtree(temp_folder, ignore_errors=True)


class State:
    app_dir = Path()
    current = "0.0.0"
    status = {"ok": False, "current": "0.0.0", "latest": "", "available": False, "notes": "", "error": ""}
    progress = {"percent": 0, "message": "", "done": False, "success": False, "error": ""}
    lock = threading.Lock()
    manifest_cache = None
    manifest_time = 0
    installing = False
    httpd = None


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
            self.send_json(State.status)
        elif path == "/progress":
            with State.lock:
                self.send_json(dict(State.progress))
        elif path == "/ping":
            self.send_json({"ok": True, "port": self.server.server_port})
        else:
            self.send_json({"error": "bulunamadı"}, 404)

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/install":
            with State.lock:
                if State.installing:
                    self.send_json({"started": False, "error": "zaten çalışıyor"})
                    return
            threading.Thread(target=install_worker, daemon=True).start()
            self.send_json({"started": True})
        elif path == "/check":
            refresh(True)
            self.send_json(State.status)
        else:
            self.send_json({"error": "bulunamadı"}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", action="store_true")
    parser.add_argument("--app", default="")
    args = parser.parse_args()
    State.app_dir = Path(args.app or Path(sys.argv[0]).resolve().parent).resolve()
    State.current = load_current(State.app_dir)
    refresh()
    if not args.service:
        print(json.dumps(State.status, ensure_ascii=False))
        return 0
    for port in PORTS:
        try:
            State.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if State.httpd is None:
        return 1
    State.httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
