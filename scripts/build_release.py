"""Build a source-only Windows ZIP from an explicit allowlist, never the workspace."""

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "LocalNarration/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def release_files(root=ROOT):
    root = root.resolve()
    files = {}
    def add(source,destination=None):
        path = root / source
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError("Missing or linked release input: " + str(source))
        component=root
        for part in path.relative_to(root).parts:
            component=component / part
            if component.is_symlink() or component.is_junction():
                raise ValueError("Linked release input: " + str(source))
        name = destination or path.relative_to(root).as_posix()
        if name in files:
            raise ValueError("Duplicate release member: " + name)
        files[name] = path.read_bytes()
    for name in ("README.md","THIRD_PARTY_NOTICES.txt","package.json","dev.bat","setup.bat","start.bat","check.bat","requirements.txt",
                 "requirements-runtime.lock.txt",
                 "scripts/serve.py","scripts/dev.mjs","scripts/setup_local.py","scripts/download_turbo.py","scripts/check_local_setup.py",
                 "app/__init__.py","app/config.py","app/main.py","app/api.py","app/audio.py","app/jobs.py",
                 "app/models.py","app/projects.py","app/segmentation.py","app/tts/__init__.py","app/tts/engine.py",
                 "app/static/index.html","app/static/docs.js","app/static/favicon.svg",
                 "app/static/vendor/swagger/swagger-ui.css","app/static/vendor/swagger/swagger-ui-bundle.js",
                 "app/static/vendor/swagger/LICENSE","app/static/vendor/swagger/NOTICE",
                 "docs/licenses/chatterbox-code-LICENSE","docs/licenses/perth-code-LICENSE",
                 "docs/licenses/turbo-README.txt","docs/licenses/ffmpeg-binary-license.txt"):
        add(name)
    # Generated assets are selected by a build receipt, never by walking the
    # static directory. Refuse stale source or modified bundles before sharing.
    ui = Path("app/static/ui")
    build_info = json.loads((root / ui / "build-info.json").read_text(encoding="utf-8"))
    for name, expected in build_info["inputs"].items():
        source = Path("frontend") / name
        add(source)
        if digest(files[source.as_posix()]) != expected:
            raise ValueError("Frontend source changed; run npm run build in frontend/: " + name)
    for name, expected in build_info["assets"].items():
        source = ui / name
        add(source)
        if digest(files[source.as_posix()]) != expected:
            raise ValueError("Frontend bundle checksum mismatch: " + name)
    add(ui / "build-info.json")
    if files["app/static/index.html"] != files["app/static/ui/index.html"]:
        raise ValueError("Frontend entry is stale; run npm run build in frontend/.")
    receipt = json.loads((root / "docs/turbo-download.json").read_text(encoding="utf-8"))
    clean = dict(repo=receipt["repo"],revision=receipt["revision"],
                 files=[{k:item[k] for k in ("name","bytes","sha256")} for item in receipt["files"]])
    files["docs/turbo-download.json"] = json.dumps(clean,indent=2).encode()
    inventory = json.loads((root / "docs/licenses/application-installed/inventory.json").read_text(encoding="utf-8"))
    public_inventory = []
    for package in inventory:
        public_inventory.append({key:package.get(key) for key in ("name","version","license","license_expression","project_urls","license_files")})
        for item in package["license_files"]:
            source = Path("docs/licenses/application-installed") / item["file"]
            if source.as_posix() not in files:
                add(source)
            if digest(files[source.as_posix()])!=item["sha256"]:
                raise ValueError("Archived license checksum mismatch: " + item["file"])
    files["docs/licenses/runtime-inventory.json"] = json.dumps(public_inventory,indent=2).encode()
    return dict(sorted(files.items()))


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Archive CRC verification failed.")
        names = archive.namelist()
        if len(names)!=len(set(names)) or any(not n.startswith(PREFIX) or ".." in Path(n).parts or "\\" in n for n in names):
            raise ValueError("Invalid release paths.")
        manifest = json.loads(archive.read(PREFIX + "MANIFEST.json"))
        if set(names)!={PREFIX+n for n in manifest["files"]} | {PREFIX+"MANIFEST.json"}:
            raise ValueError("Release contents differ from the manifest.")
        for name,meta in manifest["files"].items():
            data = archive.read(PREFIX+name)
            if len(data)!=meta["bytes"] or digest(data)!=meta["sha256"]:
                raise ValueError("Release member hash failed: " + name)
        return manifest


def build(output,root=ROOT):
    payload = release_files(root)
    manifest = dict(format_version=1,kind="source-only Windows localhost app",
                    files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in payload.items()})
    payload["MANIFEST.json"] = json.dumps(manifest,indent=2).encode()
    output = Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary = tempfile.mkstemp(dir=output.parent,suffix=".zip.tmp")
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            for name,data in sorted(payload.items()):
                info = zipfile.ZipInfo(PREFIX+name,date_time=(2026,11,8,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info,data)
        verify_archive(temporary)
        os.replace(temporary,output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    sha = digest(output.read_bytes())
    output.with_suffix(".zip.sha256").write_text(f"{sha}  {output.name}\n",encoding="ascii")
    print(json.dumps(dict(archive=str(output),bytes=output.stat().st_size,files=len(payload),sha256=sha),indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT / "dist/LocalNarration-Windows.zip")
    build(parser.parse_args().output)
