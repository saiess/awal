"""Supplement package metadata where bundled license declarations are incomplete."""
import json
from pathlib import Path
from verify_sources import get, archive, OUT


def main():
    sources = {}
    for key, repo, ref, paths in [
        ("espeakng-loader", "thewh1teagle/espeakng-loader", "main", ["LICENSE", "README.md", "pyproject.toml"]),
        ("espeak-ng", "espeak-ng/espeak-ng", "1.52.0", ["COPYING", "README.md"]),
        ("spacy-en", "explosion/spacy-models", "en_core_web_sm-3.8.0", []),
    ]:
        try:
            sha = json.loads(get(f"https://api.github.com/repos/{repo}/commits/{ref}"))["sha"]
        except Exception as e:
            sources[key] = {"error": repr(e), "repo": repo, "requested_ref": ref}
            continue
        item = {"repo": repo, "requested_ref": ref, "revision": sha, "evidence": []}
        for path in paths:
            try:
                item["evidence"].append(archive(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}", key + "-" + Path(path).name))
            except Exception as e:
                item.setdefault("errors", []).append({"path": path, "error": repr(e)})
        sources[key] = item
    (OUT / "supporting-revisions.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    print(json.dumps(sources, indent=2))


if __name__ == "__main__":
    main()
