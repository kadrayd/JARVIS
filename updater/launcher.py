import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def main():
    app_dir = Path(sys.executable).resolve().parent
    executable = next(
        (
            item
            for item in app_dir.glob("JARVIS *.exe")
            if not item.name.lower().startswith(("setup", "jarvisupdater"))
        ),
        None,
    )
    if executable is None:
        return 1
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [str(executable)],
        cwd=str(app_dir),
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    updater_source = app_dir / "JARVISUpdater.exe"
    updater_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "JARVIS Updater"
    updater_target = updater_dir / "JARVISUpdater.exe"
    if updater_source.exists():
        updater_dir.mkdir(parents=True, exist_ok=True)
        if not updater_target.exists():
            shutil.copy2(updater_source, updater_target)
    if updater_target.exists():
        subprocess.Popen(
            [str(updater_target), "--service", "--app", str(app_dir)],
            cwd=str(updater_dir),
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    (app_dir / "launch-ok.flag").write_text(str(time.time()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
