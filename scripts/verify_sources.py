"""Archive exact official revisions, model file inventory, and license evidence. No weights."""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "licenses"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "local-tts-benchmark"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def archive(url, name):
    data = get(url)
    (OUT / name).write_bytes(data)
    return {"url": url, "file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "models": {}, "code": {}}
    for key, repo in (("chatterbox", "ResembleAI/chatterbox"), ("turbo", "ResembleAI/chatterbox-turbo"), ("kokoro", "hexgrad/Kokoro-82M")):
        meta = json.loads(get(f"https://huggingface.co/api/models/{repo}?blobs=true"))
        sha = meta["sha"]
        item = {"repo": repo, "revision": sha, "declared_license": meta.get("cardData", {}).get("license"), "files": meta["siblings"], "evidence": []}
        for f in meta["siblings"]:
            name = f["rfilename"]
            if name in ("README.md", "LICENSE", "LICENSE.txt", "VOICES.md", "config.json"):
                item["evidence"].append(archive(f"https://huggingface.co/{repo}/resolve/{sha}/{name}", key + "-" + name))
        report["models"][key] = item
    for key, repo in (("chatterbox", "resemble-ai/chatterbox"), ("kokoro", "hexgrad/kokoro"), ("misaki", "hexgrad/misaki"), ("perth", "resemble-ai/Perth")):
        meta = json.loads(get(f"https://api.github.com/repos/{repo}/commits/HEAD"))
        sha = meta["sha"]
        item = {"repo": repo, "revision": sha, "evidence": []}
        for name in ("LICENSE", "pyproject.toml", "README.md"):
            try:
                item["evidence"].append(archive(f"https://raw.githubusercontent.com/{repo}/{sha}/{name}", key + "-code-" + name))
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                item.setdefault("missing", []).append(name)
        report["code"][key] = item
    (OUT / "revisions.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: {n: v["revision"] for n, v in report[k].items()} for k in ("models", "code")}, indent=2))


if __name__ == "__main__":
    main()
