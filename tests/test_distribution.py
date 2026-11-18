import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import build_release, setup_local
from scripts import download_qwen
from app import config


def test_archive_contains_only_selected_source_and_sanitized_receipts(tmp_path):
    archive = tmp_path / "release.zip"
    manifest = build_release.build(archive)
    assert manifest == build_release.verify_archive(archive)
    names = set(manifest["files"])
    assert {"setup.bat","start.bat","check.bat","scripts/download_qwen.py","app/static/index.html"} <= names
    assert not any(part in {"data","website-data","test-results",".git","__pycache__","persistence","results"}
                   or part.startswith(".venv") for name in names for part in Path(name).parts)
    assert not any(name.endswith((".wav",".ogg",".mp3",".pyc",".sqlite3",".exe")) for name in names)
    assert "docs/reference-inspection.json" not in names
    assert "app/static/vendor/swagger/LICENSE" in names
    assert "frontend/src/App.tsx" in names
    assert "frontend/package-lock.json" in names
    assert "app/static/ui/licenses/react.LICENSE" in names
    assert "app/static/app.js" not in names
    assert {name for name in names if name.lower().endswith('.md')} == {'README.md'}
    assert 'THIRD_PARTY_NOTICES.txt' in names
    assert not any("node_modules" in Path(name).parts for name in names)
    with zipfile.ZipFile(archive) as z:
        receipt=json.loads(z.read("LocalNarration/docs/qwen-download.json"))
        assert {"repo","revision","files","code_revision","code_files"} <= set(receipt)
        assert "snapshot" not in receipt
        for name in names:
            assert b"C:\\\\Users\\\\saide" not in z.read("LocalNarration/"+name)
        z.extractall(tmp_path / "extracted")
    root=tmp_path / "extracted/LocalNarration"
    result=subprocess.run([os.sys.executable,"-c",
        "from app.config import Settings; from app.projects import Store; s=Store(Settings()); assert s.narrator() is None; assert s.list_projects()==[]"],
        cwd=root,capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_archive_crc_or_manifest_tampering_is_detected(tmp_path):
    archive=tmp_path / "release.zip"
    build_release.build(archive)
    with zipfile.ZipFile(archive,"a") as z:
        z.writestr("LocalNarration/unexpected-secret.txt","must not be present")
    with pytest.raises(ValueError,match="manifest"):
        build_release.verify_archive(archive)


def test_persistent_cache_config_and_environment_precedence(tmp_path,monkeypatch):
    monkeypatch.delenv("HF_HOME",raising=False)
    monkeypatch.setattr(config,"ROOT",tmp_path)
    persistent=tmp_path / "persistent-models"
    (tmp_path / ".local-config.json").write_text(json.dumps(dict(schema_version=1,cache_root=str(persistent))))
    assert config.Settings().cache_root==persistent
    override=tmp_path / "override"
    monkeypatch.setenv("HF_HOME",str(override))
    assert config.Settings().cache_root==override


def test_setup_default_cache_is_persistent_and_existing_choice_retained(tmp_path,monkeypatch):
    monkeypatch.delenv("HF_HOME",raising=False)
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path / "user-data"))
    expected=tmp_path / "user-data/LocalNarration/huggingface"
    assert setup_local.cache_location(tmp_path)==expected
    selected=tmp_path / "chosen"
    (tmp_path / ".local-config.json").write_text(json.dumps(dict(schema_version=1,cache_root=str(selected))))
    assert setup_local.cache_location(tmp_path)==selected


def test_setup_dry_run_does_not_create_files_or_launch_install(tmp_path,monkeypatch):
    monkeypatch.setattr(setup_local,"ROOT",tmp_path)
    monkeypatch.setattr(setup_local.sys,"platform","win32")
    monkeypatch.setattr(setup_local.sys,"version_info",(3,12,2))
    monkeypatch.setattr(setup_local.shutil,"which",lambda name:"git.exe")
    monkeypatch.setattr(setup_local,"cache_location",lambda:tmp_path / "models")
    monkeypatch.setattr(setup_local,"run",lambda *a,**k:pytest.fail("Dry run invoked installer"))
    setup_local.install(dry_run=True)
    assert list(tmp_path.iterdir())==[]


def test_wrong_existing_environment_is_not_deleted_or_recreated(tmp_path,monkeypatch):
    monkeypatch.setattr(setup_local,"ROOT",tmp_path)
    monkeypatch.setattr(setup_local.sys,"platform","win32")
    monkeypatch.setattr(setup_local.sys,"version_info",(3,12,2))
    monkeypatch.setattr(setup_local.shutil,"which",lambda name:"git.exe")
    monkeypatch.setattr(setup_local,"cache_location",lambda:tmp_path / "models")
    python=tmp_path / ".venv-qwen3/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"existing environment")
    data=tmp_path / "data/project.json"
    data.parent.mkdir()
    data.write_text("private project")
    monkeypatch.setattr(setup_local.subprocess,"run",lambda *a,**kw:subprocess.CompletedProcess(a,0,"NVIDIA GPU",""))
    def wrong_python(*args,**kwargs):
        raise subprocess.CalledProcessError(1,args[0])
    monkeypatch.setattr(setup_local,"run",wrong_python)
    with pytest.raises(subprocess.CalledProcessError):
        setup_local.install()
    assert python.read_bytes()==b"existing environment"
    assert data.read_text()=="private project"


@pytest.mark.parametrize("corrupt",[False,True])
def test_setup_download_is_pinned_and_never_rewrites_hash_receipt(tmp_path,monkeypatch,corrupt):
    monkeypatch.setenv("HF_HOME",str(tmp_path / "cache"))
    monkeypatch.setenv("HF_HUB_DISABLE_XET","1")
    model=tmp_path / "snapshot"
    model.mkdir()
    asset=model / "model.bin"
    asset.write_bytes(b"approved")
    receipt=dict(repo=config.MODEL_REPO,revision=config.MODEL_REVISION,
                 files=[dict(name="model.bin",bytes=8,sha256=build_release.digest(b"approved"))])
    docs=tmp_path / "docs"
    docs.mkdir()
    record=docs / "qwen-download.json"
    record.write_text(json.dumps(receipt))
    original=record.read_bytes()
    if corrupt:
        asset.write_bytes(b"modified")
    monkeypatch.setattr(download_qwen,"ROOT",tmp_path)
    import app.tts.engine as engine
    def not_cached(*a,**kw): raise FileNotFoundError("not cached")
    monkeypatch.setattr(engine,"local_snapshot",not_cached)
    monkeypatch.setattr(download_qwen,"Settings",lambda:SimpleNamespace(cache_root=tmp_path / "cache",qwen_model_dir=None))
    def snapshot(repo,**kwargs):
        assert repo==config.MODEL_REPO
        assert kwargs["revision"]==config.MODEL_REVISION
        assert kwargs["allow_patterns"]==["model.bin"]
        return str(model)
    monkeypatch.setitem(sys.modules,"huggingface_hub",SimpleNamespace(snapshot_download=snapshot))
    if corrupt:
        with pytest.raises(RuntimeError,match="checksum mismatch"):
            download_qwen.main()
    else:
        download_qwen.main()
    assert record.read_bytes()==original


@pytest.mark.parametrize("changed",["source","bundle"])
def test_release_refuses_stale_or_modified_frontend(monkeypatch,changed):
    root=build_release.ROOT
    info=json.loads((root / "app/static/ui/build-info.json").read_text(encoding="utf-8"))
    relative=Path("frontend/src/App.tsx") if changed=="source" else Path("app/static/ui") / next(n for n in info["assets"] if n.endswith('.js'))
    target=(root / relative).resolve()
    original=Path.read_bytes
    def altered(path):
        value=original(path)
        return value+b'\nmodified' if path.resolve()==target else value
    monkeypatch.setattr(Path,"read_bytes",altered)
    with pytest.raises(ValueError,match="Frontend (source changed|bundle checksum mismatch)"):
        build_release.release_files()
