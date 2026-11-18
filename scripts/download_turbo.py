"""Explicit setup-time download; never rewrites the trusted model receipt."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from app.config import Settings
from scripts.legacy_turbo_engine import MODEL_REPO, MODEL_REVISION
from app.projects import file_hash


def download():
    settings = Settings()
    os.environ.setdefault("HF_HOME",str(settings.cache_root))
    # Standard HTTP provides predictable Windows downloads. The pinned Turbo
    # implementation also falls back to HTTP when the optional Xet path fails.
    # Set this before importing huggingface_hub, which reads it at import time.
    if os.name == "nt":
        os.environ.setdefault("HF_HUB_DISABLE_XET","1")
    from huggingface_hub import snapshot_download
    receipt = json.loads((ROOT / "docs/turbo-download.json").read_text(encoding="utf-8"))
    if receipt["repo"] != MODEL_REPO or receipt["revision"] != MODEL_REVISION:
        raise ValueError("Model receipt differs from the approved revision.")
    folder = Path(snapshot_download(MODEL_REPO,revision=MODEL_REVISION,
                                  allow_patterns=[f["name"] for f in receipt["files"]],
                                  cache_dir=str(settings.cache_root / "hub")))
    for item in receipt["files"]:
        path = folder / item["name"]
        if not path.is_file() or path.stat().st_size!=item["bytes"] or file_hash(path)!=item["sha256"]:
            raise ValueError("Downloaded model failed verification: " + item["name"])
    print("Pinned Turbo model downloaded; all SHA256 checks passed.")


if __name__ == "__main__":
    try:
        download()
    except Exception as error:
        print(f"Model download stopped: {error}. Retry setup.bat with internet access.",file=sys.stderr)
        raise SystemExit(1)
