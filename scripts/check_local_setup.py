"""Read-only Windows PC readiness check. Never installs or downloads anything."""

import argparse
import importlib.metadata as metadata
import json
import os
import platform
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import CODE_REVISION, MODEL_REPO, MODEL_REVISION, Settings
from app.projects import file_hash


def inspect(*, verify_model=False, progress=None):
    checks = []

    def check(name, probe):
        if progress:
            progress(f"Checking {name}...", flush=True)
        try:
            detail = probe()
            checks.append(dict(name=name, ok=True, detail=detail))
        except Exception as error:
            checks.append(dict(name=name, ok=False, detail=str(error)))
        if progress:
            item = checks[-1]
            progress(f"[{'OK' if item['ok'] else 'FAIL'}] {item['name']}: {item['detail']}", flush=True)

    def runtime():
        if sys.platform != "win32" or struct.calcsize("P") != 8 or sys.version_info[:2] != (3, 12):
            raise RuntimeError("This release requires 64-bit Windows and Python 3.12. See README.md.")
        return f"{platform.system()} {platform.release()}, Python {platform.python_version()} (64-bit)"

    def dependencies():
        result = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr).strip() + " Restore the pinned requirements.txt environment.")
        for package in ("fastapi", "uvicorn", "torch", "torchaudio", "soundfile", "imageio-ffmpeg", "huggingface-hub", "chatterbox-tts"):
            metadata.version(package)
        dist = metadata.distribution("chatterbox-tts")
        origin = json.loads(dist.read_text("direct_url.json") or "{}")
        if dist.version != "0.1.7" or origin.get("vcs_info", {}).get("commit_id") != CODE_REVISION:
            raise RuntimeError("Chatterbox differs from the approved code revision. Restore requirements.txt.")
        return "Dependencies consistent; approved Chatterbox code installed."

    def gpu():
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("NVIDIA CUDA is unavailable. Intel/AMD graphics and CPU-only PCs are unsupported by this release.")
        # Availability alone does not prove this GPU can execute the installed CUDA kernels.
        value = torch.ones(8, device="cuda").sum().item()
        if value != 8:
            raise RuntimeError("CUDA computation failed.")
        device = torch.cuda.get_device_properties(torch.cuda.current_device())
        return f"{device.name}, {device.total_memory / 1024**3:.1f} GiB VRAM; CUDA computation passed. Validated baseline: RTX 4070 Laptop (8 GB)."

    def ffmpeg():
        import imageio_ffmpeg
        executable = os.environ.get("TTS_FFMPEG") or imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise RuntimeError("FFmpeg could not start. Check TTS_FFMPEG or restore imageio-ffmpeg.")
        return result.stdout.splitlines()[0]

    def model():
        from huggingface_hub import snapshot_download
        receipt = json.loads((ROOT / "docs/turbo-download.json").read_text(encoding="utf-8"))
        if receipt["repo"] != MODEL_REPO or receipt["revision"] != MODEL_REVISION:
            raise RuntimeError("Model receipt does not match the approved model revision.")
        try:
            folder = Path(snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_files_only=True,
                                           allow_patterns=[item["name"] for item in receipt["files"]],
                                           cache_dir=str(Settings().cache_root / "hub")))
        except Exception as error:
            raise RuntimeError("Pinned Turbo model is not cached. Run the model download command in README.md.") from error
        for item in receipt["files"]:
            path = folder / item["name"]
            if not path.is_file() or path.stat().st_size != item["bytes"]:
                raise RuntimeError("Missing or incomplete model asset: " + item["name"])
            if verify_model and file_hash(path) != item["sha256"]:
                raise RuntimeError("Model checksum mismatch: " + item["name"])
        return f"{len(receipt['files'])} pinned model files present" + ("; SHA256 checks passed." if verify_model else ". Full checksums run when the engine loads.")

    check("Windows / Python", runtime)
    check("Dependencies", dependencies)
    check("NVIDIA GPU", gpu)
    check("Audio export", ffmpeg)
    check("Local Turbo model", model)
    return dict(ok=all(c["ok"] for c in checks), checks=checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-model", action="store_true", help="Hash all cached model files as well as checking sizes")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report")
    args = parser.parse_args()
    report = inspect(verify_model=args.verify_model, progress=None if args.json else print)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\nPC ready. Run start.bat and open http://127.0.0.1:8000" if report["ok"] else
              "\nSetup incomplete. Follow README.md; nothing was installed or downloaded.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
