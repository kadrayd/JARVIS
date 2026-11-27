import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPDATER = ROOT / "updater"


def build_exes():
    specs = [
        (UPDATER / "updater_service.py", "JARVISUpdater"),
        (UPDATER / "launcher.py", "setup"),
    ]
    for source, name in specs:
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            name,
            "--distpath",
            str(UPDATER / "build" / "dist"),
            "--workpath",
            str(UPDATER / "build" / "work"),
            "--specpath",
            str(UPDATER / "build"),
            str(source),
        ]
        subprocess.run(command, check=True, cwd=str(UPDATER))


def sign_exes():
    dist = UPDATER / "build" / "dist"
    command = (
        "$cert = Get-Item 'Cert:\\CurrentUser\\My\\39D7B3C40713F948D090CE28F65707AAEB62734F' -ErrorAction SilentlyContinue; "
        "if (-not $cert) { $cert = Get-ChildItem 'Cert:\\CurrentUser\\My' -CodeSigningCert | "
        "Where-Object { $_.NotAfter -gt (Get-Date) } | "
        "Sort-Object NotAfter -Descending | Select-Object -First 1 }; "
        "if ($cert) { Get-ChildItem '" + str(dist) + "\\*.exe' | ForEach-Object { "
        "Set-AuthenticodeSignature -FilePath $_.FullName -Certificate $cert -HashAlgorithm SHA256 | Out-Null } }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package(source_dir, version, output_dir):
    source = Path(source_dir).resolve()
    if not source.is_dir():
        raise SystemExit("Kaynak klasör bulunamadı: " + str(source))
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    dist = UPDATER / "build" / "dist"
    shutil.copy2(dist / "JARVISUpdater.exe", source / "JARVISUpdater.exe")
    shutil.copy2(dist / "setup.exe", source / "setup.exe")
    bootstrapper = UPDATER / "WebView2Bootstrapper.exe"
    if bootstrapper.exists():
        shutil.copy2(bootstrapper, source / "WebView2Bootstrapper.exe")
    (source / "version.json").write_text(
        json.dumps({"version": version}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    archive = out / ("JARVIS-" + version + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for item in source.rglob("*"):
            if item.is_file() and item.name != "launch-ok.flag":
                zipped.write(item, item.relative_to(source))
    manifest = {
        "version": version,
        "url": "https://github.com/kadrayd/JARVIS/releases/download/v"
        + version
        + "/JARVIS-"
        + version
        + ".zip",
        "sha256": sha256(archive),
        "notes": "JARVIS " + version + " - uygulama içi güncelleme sistemi",
    }
    (out / "updates.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"zip": str(archive), "sha256": manifest["sha256"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--source", default="")
    parser.add_argument("--version", default="3.2.0")
    parser.add_argument("--output", default=str(ROOT / "release"))
    args = parser.parse_args()
    if args.build:
        build_exes()
        sign_exes()
    if args.source:
        package(args.source, args.version, args.output)


if __name__ == "__main__":
    main()
