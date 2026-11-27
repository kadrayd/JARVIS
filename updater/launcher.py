import ctypes
import os
import shutil
import subprocess
import sys
import time
import traceback
import winreg
from pathlib import Path

CERT_ID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
LOG_NAME = "launcher.log"


def unblock_folder(folder):
    count = 0
    for item in folder.rglob("*"):
        if not item.is_file():
            continue
        stream = "\\\\?\\" + str(item) + ":Zone.Identifier"
        if ctypes.windll.kernel32.DeleteFileW(stream):
            count += 1
    return count


def log(folder, message):
    try:
        with open(folder / LOG_NAME, "a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + message + "\n")
    except Exception:
        pass


def alert(title, message):
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


def webview2_installed():
    locations = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\" + CERT_ID),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\" + CERT_ID),
        (winreg.HKEY_CURRENT_USER, "SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\" + CERT_ID),
    ]
    for root, path in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                value, _ = winreg.QueryValueEx(key, "pv")
                if value:
                    return True
        except OSError:
            pass
    return False


def ensure_webview2(app_dir):
    if webview2_installed():
        return True
    installer = app_dir / "WebView2Bootstrapper.exe"
    if not installer.exists():
        alert(
            "JARVIS",
            "Microsoft Edge WebView2 Runtime eksik.\nKurulum dosyasını indirip çalıştırın: "
            "https://developer.microsoft.com/microsoft-edge/webview2/",
        )
        return False
    log(app_dir, "WebView2 kuruluyor")
    try:
        subprocess.run(
            [str(installer), "/silent", "/install"],
            cwd=str(app_dir),
            timeout=420,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        log(app_dir, "WebView2 kurulum hatası: " + str(exc))
    if webview2_installed():
        log(app_dir, "WebView2 kuruldu")
        return True
    alert("JARVIS", "WebView2 Runtime kurulamadı. İnternet bağlantısını kontrol edip yeniden deneyin.")
    return False


def log_tail(app_dir, limit=4000):
    path = Path(os.environ.get("APPDATA", "")) / "JARVIS 3.0" / "jarvis.log"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[-limit:]
    except Exception:
        return "jarvis.log okunamadı: " + str(path)


def start_updater(app_dir, flags):
    source = app_dir / "JARVISUpdater.exe"
    target_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "JARVIS Updater"
    target = target_dir / "JARVISUpdater.exe"
    if source.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
    if target.exists():
        subprocess.Popen(
            [str(target), "--service", "--app", str(app_dir)],
            cwd=str(target_dir),
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log(app_dir, "Güncelleyici başlatıldı")


def start_vision(app_dir, flags):
    source = app_dir / "JARVISVision.exe"
    if not source.exists():
        log(app_dir, "JARVISVision.exe bulunamadı")
        return
    subprocess.Popen(
        [str(source), "--service"],
        cwd=str(app_dir),
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log(app_dir, "Kamera hareket servisi başlatıldı")


def main():
    app_dir = Path(sys.executable).resolve().parent
    try:
        log(app_dir, "Başlatılıyor: " + str(app_dir))
        blocked = unblock_folder(app_dir)
        if blocked:
            log(app_dir, "İnternet işaretleri kaldırıldı: " + str(blocked))
        if not ensure_webview2(app_dir):
            return 1
        executable = app_dir / "JARVIS-Core.exe"
        if not executable.exists():
            executable = next(
                (
                    item
                    for item in app_dir.glob("JARVIS*.exe")
                    if item.resolve() != Path(sys.executable).resolve()
                    and not item.name.lower().startswith(("setup", "jarvisupdater", "webview2"))
                ),
                None,
            )
        if executable is None:
            alert("JARVIS", "Uygulama dosyası bulunamadı: JARVIS-Core.exe")
            return 1
        log(app_dir, "Uygulama: " + executable.name)
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        process = subprocess.Popen(
            [str(executable)],
            cwd=str(app_dir),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        start_updater(app_dir, flags)
        start_vision(app_dir, flags)
        time.sleep(5)
        if process.poll() is None:
            (app_dir / "launch-ok.flag").write_text(str(time.time()), encoding="utf-8")
        try:
            code = process.wait(timeout=15)
            detail = log_tail(app_dir)
            log(app_dir, "Uygulama erken kapandı, kod=" + str(code))
            alert("JARVIS açılamadı.", (detail or "Ayrıntı yok.")[-3000:])
        except subprocess.TimeoutExpired:
            log(app_dir, "Uygulama çalışıyor")
        return 0
    except Exception:
        detail = traceback.format_exc()
        log(app_dir, detail)
        alert("JARVIS açılamadı.", detail[-3000:])
        return 1


if __name__ == "__main__":
    sys.exit(main())
