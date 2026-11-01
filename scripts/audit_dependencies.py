"""Archive installed dependency declarations and bundled license texts (not legal clearance)."""
import hashlib
import importlib.metadata as md
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
label = sys.argv[1]
out = root / "docs/licenses" / (label + "-installed")
out.mkdir(parents=True, exist_ok=True)
rows = []
for dist in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
    m = dist.metadata
    row = {"name": m["Name"], "version": dist.version, "license": m.get("License"),
           "license_expression": m.get("License-Expression"),
           "classifiers": [v for v in m.get_all("Classifier", []) if "License" in v],
           "project_urls": m.get_all("Project-URL", []), "license_files": [], "bundled_assets": []}
    for file in dist.files or []:
        name = str(file).replace("\\", "/")
        if (name.startswith("perth/perth_net/pretrained/") or name == "espeakng_loader/espeak-ng.dll" or
                (name.startswith("imageio_ffmpeg/binaries/") and name.endswith(".exe")) or
                (name.startswith("en_core_web_sm/en_core_web_sm-") and "__pycache__" not in name)):
            asset = Path(dist.locate_file(file))
            if asset.is_file():
                row["bundled_assets"].append({"path": name, "bytes": asset.stat().st_size,
                                               "sha256": hashlib.sha256(asset.read_bytes()).hexdigest()})
        if ".dist-info/" not in name or not re.search(r"(license|copying|notice)", name, re.I):
            continue
        path = Path(dist.locate_file(file))
        if path.is_file():
            data = path.read_bytes()
            target = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
            (out / target).write_bytes(data)
            row["license_files"].append({"file": target, "sha256": hashlib.sha256(data).hexdigest()})
    rows.append(row)
(out / "inventory.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(json.dumps([{k:r[k] for k in ("name", "version", "license_expression", "classifiers")} for r in rows], indent=2))
