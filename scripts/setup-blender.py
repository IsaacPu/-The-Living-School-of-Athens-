"""Install a hash-verified official portable Blender inside this workspace only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

import requests


ROOT = Path(__file__).resolve().parent.parent
VERSION = "4.5.15"
NAME = f"blender-{VERSION}-windows-x64"
BASE = "https://download.blender.org/release/Blender4.5/"


def main() -> None:
    tools = ROOT / ".tools"
    downloads = tools / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / f"{NAME}.zip"
    session = requests.Session()
    session.trust_env = False
    checksum_response = session.get(BASE + f"blender-{VERSION}.sha256", timeout=(10, 30))
    checksum_response.raise_for_status()
    expected = next(
        line.split()[0].lower()
        for line in checksum_response.text.splitlines()
        if line.strip().endswith(archive.name)
    )
    if len(expected) != 64:
        raise RuntimeError("Official checksum is not SHA-256.")
    if not archive.exists():
        partial = archive.with_suffix(".zip.part")
        with session.get(BASE + archive.name, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", "0"))
            written = 0
            last_report = time.monotonic()
            with partial.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    written += len(chunk)
                    if time.monotonic() - last_report >= 20:
                        print(json.dumps({"stage": "download", "bytes": written, "total": total}), flush=True)
                        last_report = time.monotonic()
            if total and written != total:
                raise RuntimeError("Official download length mismatch; partial retained.")
        partial.replace(archive)
    with archive.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != expected:
        raise RuntimeError("Official archive SHA-256 mismatch; archive retained, not executed.")
    print(json.dumps({"stage": "checksum_verified", "sha256": actual}), flush=True)
    target = tools / "blender"
    target.mkdir(parents=True, exist_ok=True)
    executable = target / NAME / "blender.exe"
    if not executable.exists():
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                resolved = (target / member.filename).resolve()
                if not resolved.is_relative_to(target.resolve()):
                    raise RuntimeError("Archive member escapes the project tool directory.")
            bad = package.testzip()
            if bad is not None:
                raise RuntimeError(f"Archive CRC failure: {bad}")
            package.extractall(target)
    result = subprocess.run([str(executable), "--version"], capture_output=True, text=True, check=True, timeout=45)
    version_line = result.stdout.splitlines()[0]
    if not version_line.startswith(f"Blender {VERSION}"):
        raise RuntimeError("Extracted executable reports an unexpected version.")
    record = {
        "version": VERSION,
        "executable": str(executable),
        "source": BASE + archive.name,
        "checksum_source": BASE + f"blender-{VERSION}.sha256",
        "archive_sha256": actual,
        "version_check": version_line,
        "installation_scope": "project_portable_only",
        "system_path_or_registry_modified": False,
    }
    (tools / "blender-runtime.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage": "ready", **record}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
