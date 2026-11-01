"""Fetch only benchmark assets from pinned official Hugging Face revisions."""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(tempfile.gettempdir()) / "local-youtube-tts-cache"
os.environ.setdefault("HF_HOME", str(CACHE / "huggingface"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model", choices=["kokoro", "chatterbox", "turbo"])
    args = p.parse_args()
    from huggingface_hub import snapshot_download
    sources = json.loads((ROOT / "docs/licenses/revisions.json").read_text())
    model = sources["models"][args.model]
    patterns = {
        "kokoro": ["config.json", "kokoro-v1_0.pth", "voices/af_heart.pt"],
        "chatterbox": ["ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors", "tokenizer.json"],
        "turbo": ["*.json", "*.txt", "*.yaml", "ve.safetensors", "t3_turbo_v1.safetensors", "s3gen_meanflow.safetensors"],
    }[args.model]
    location = Path(snapshot_download(model["repo"], revision=model["revision"], allow_patterns=patterns))
    files = []
    for file in location.rglob("*"):
        if file.is_file():
            h = hashlib.sha256()
            with file.open("rb") as f:
                for data in iter(lambda: f.read(8 * 1024 * 1024), b""):
                    h.update(data)
            name = file.relative_to(location).as_posix()
            upstream = next(f for f in model["files"] if f["rfilename"] == name)
            expected = upstream.get("lfs", {}).get("sha256")
            if expected and expected != h.hexdigest():
                raise ValueError(f"Official LFS hash mismatch: {name}")
            files.append({"name": name, "bytes": file.stat().st_size, "sha256": h.hexdigest(),
                          "upstream_lfs_sha256": expected, "lfs_hash_matches": h.hexdigest() == expected if expected else None})
    report = {"repo": model["repo"], "revision": model["revision"], "snapshot": str(location), "files": files,
              "total_bytes": sum(f["bytes"] for f in files)}
    (ROOT / f"docs/{args.model}-download.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
