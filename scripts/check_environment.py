"""Read-only environment probe; optional JSON file, always prints JSON."""
import argparse
import ctypes
import importlib.metadata as md
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return {"command": args, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"command": args, "error": repr(e)}


def inspect():
    d = {"platform": platform.platform(), "python": sys.version, "executable": sys.executable,
         "disk": dict(zip(("total", "used", "free"), shutil.disk_usage(Path.cwd()))),
         "nvidia_smi": command(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free", "--format=csv"]),
         "ffmpeg": shutil.which("ffmpeg")}
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in
                        ("total_physical", "available_physical", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]
        memory = MemoryStatus()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            d["ram"] = {"total_bytes": memory.total_physical, "available_bytes": memory.available_physical}
    if not d["ffmpeg"]:
        try:
            import imageio_ffmpeg
            d["ffmpeg"] = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    if d["ffmpeg"]:
        d["ffmpeg_version"] = command([d["ffmpeg"], "-version"])
    try:
        import torch
        d["torch"] = {"version": torch.__version__, "cuda_build": torch.version.cuda,
                      "available": torch.cuda.is_available()}
        if torch.cuda.is_available():
            x = torch.randn(1024, 1024, device="cuda")
            y = x @ x.T
            torch.cuda.synchronize()
            d["torch"].update(device=torch.cuda.get_device_name(), finite=bool(y.isfinite().all()),
                              peak_allocated_bytes=torch.cuda.max_memory_allocated())
    except Exception as e:
        d["torch_error"] = repr(e)
    for name in ("torch", "torchaudio", "kokoro", "chatterbox-tts"):
        try:
            d[name + "_distribution"] = md.version(name)
        except md.PackageNotFoundError:
            pass
    try:
        import torchaudio
        d["torchaudio_import"] = torchaudio.__version__
    except Exception as e:
        d["torchaudio_error"] = repr(e)
    return d


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    output = json.dumps(inspect(), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)

