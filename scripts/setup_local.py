"""Guided Windows setup. Explicitly run setup.bat to install/download locally."""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, env=None):
    subprocess.run([str(part) for part in command], cwd=ROOT, env=env, check=True)


def cache_location(root=ROOT):
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser().resolve()
    config = root / ".local-config.json"
    if config.exists():
        record = json.loads(config.read_text(encoding="utf-8"))
        path = Path(record["cache_root"])
        if record.get("schema_version") != 1 or not path.is_absolute():
            raise ValueError("Invalid .local-config.json. Correct its absolute cache_root path before retrying.")
        return path
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise ValueError("LOCALAPPDATA is unavailable. Set HF_HOME to a persistent model-cache directory.")
    return Path(local) / "LocalNarration" / "huggingface"


def install(*, dry_run=False):
    if sys.platform != "win32" or struct.calcsize("P") != 8 or sys.version_info[:2] != (3,12):
        raise ValueError("Install 64-bit Python 3.12 and run setup.bat again. Other Python versions are unsupported.")
    if not shutil.which("git"):
        raise ValueError("Git for Windows is required for the pinned source packages. Install it, reopen the terminal, and retry.")
    cache = cache_location()
    python = ROOT / ".venv-chatterbox/Scripts/python.exe"
    print("Local Narration setup: Windows / NVIDIA CUDA. No accounts or hosting.",flush=True)
    print(f"Environment: {python.parent.parent}\nPersistent model cache: {cache}",flush=True)
    print("Installs the pinned Python packages and downloads the pinned Turbo model. Internet is required.",flush=True)
    print("Existing projects and recordings are preserved. Rerun setup.bat to retry an interrupted setup.",flush=True)
    if dry_run:
        print("Dry run: no environment, configuration, packages, or model files changed.")
        return
    probe = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],
                           capture_output=True,text=True,timeout=20)
    if probe.returncode:
        raise ValueError("NVIDIA driver/GPU not found. This release does not support Intel/AMD graphics or CPU-only generation.")
    print(probe.stdout.strip(),flush=True)
    print(f"Free installation-disk space: {shutil.disk_usage(ROOT).free / 1024**3:.1f} GiB. Allow roughly 20 GB for setup and downloads, plus project audio.",flush=True)
    environment = python.parent.parent
    if environment.exists():
        if not python.is_file():
            raise ValueError("Existing .venv-chatterbox is incomplete. Preserve your data and move that environment aside before retrying.")
        run([python,"-c","import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8, 'Existing environment must use 64-bit Python 3.12'"])
    else:
        venv.EnvBuilder(with_pip=True).create(environment)
    # Keep the tested installer version rather than silently updating to latest.
    run([python,"-m","pip","install","--disable-pip-version-check","--no-deps","pip==24.0"])
    run([python,"-m","pip","install","--disable-pip-version-check","--no-deps","-r",ROOT / "requirements.txt"])
    run([python,"-m","pip","check"])
    # Save machine-specific paths locally, never in the distribution/model receipt.
    config = ROOT / ".local-config.json"
    temporary = config.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(dict(schema_version=1,cache_root=str(cache)),indent=2),encoding="utf-8")
    os.replace(temporary,config)
    env = dict(os.environ,HF_HOME=str(cache))
    env.pop("HF_HUB_OFFLINE",None)
    env.pop("TRANSFORMERS_OFFLINE",None)
    run([python,ROOT / "scripts/download_turbo.py"],env=env)
    run([python,ROOT / "scripts/check_local_setup.py","--verify-model"],env=env)
    print("\nSetup complete. Run start.bat, open http://127.0.0.1:8000, then add your own authorized voice reference.",flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run",action="store_true")
    args = parser.parse_args()
    try:
        install(dry_run=args.dry_run)
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print(f"\nSetup stopped: {error}\nNothing was deleted. Correct the issue and run setup.bat again.",file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
