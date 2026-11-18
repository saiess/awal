"""Explicit setup-only download; application inference always uses local snapshots."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import Settings, MODEL_REPO, MODEL_REVISION
from app.projects import file_hash, atomic_json


def main():
    settings = Settings()
    from app.tts.engine import local_snapshot
    try:
        folder = local_snapshot(settings)
        print(f"Verified existing pinned Qwen model: {folder}")
        return
    except (OSError, RuntimeError):
        pass
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    from huggingface_hub import snapshot_download
    receipt = json.loads((ROOT/'docs/qwen-download.json').read_text(encoding='utf-8'))
    folder = Path(snapshot_download(MODEL_REPO, revision=MODEL_REVISION,
        allow_patterns=[x['name'] for x in receipt['files']], cache_dir=str(settings.cache_root/'hub')))
    for item in receipt['files']:
        if file_hash(folder/item['name']) != item['sha256']:
            raise RuntimeError('Downloaded Qwen asset checksum mismatch: '+item['name'])
    config = ROOT/'.local-config.json'
    record = json.loads(config.read_text(encoding='utf-8')) if config.exists() else {}
    record.update(schema_version=1, cache_root=str(settings.cache_root), qwen_model_dir=str(folder))
    atomic_json(config, record)
    print(f'Pinned Qwen snapshot verified: {folder}')


if __name__ == '__main__':
    main()
