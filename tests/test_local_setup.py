"""Readiness failures must be actionable and must never fetch assets."""

import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import check_local_setup as checker


@pytest.fixture
def pc_check(tmp_path,monkeypatch):
    monkeypatch.setattr(checker.sys,"platform","win32")
    monkeypatch.setattr(checker.sys,"version_info",(3,12,2))
    monkeypatch.setattr(checker.metadata,"version",lambda name:"installed")
    origin=json.dumps({"vcs_info":{"commit_id":checker.CODE_REVISION}})
    monkeypatch.setattr(checker.metadata,"distribution",lambda name:SimpleNamespace(version="0.1.7",read_text=lambda name:origin))
    monkeypatch.setattr(checker.subprocess,"run",lambda *a,**kw:subprocess.CompletedProcess(a,0,"Version available\n",""))
    monkeypatch.setitem(sys.modules,"imageio_ffmpeg",SimpleNamespace(get_ffmpeg_exe=lambda:"ffmpeg.exe"))
    monkeypatch.setitem(sys.modules,"torch",SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False)))
    model=tmp_path / "snapshot"
    model.mkdir()
    asset=model / "model.bin"
    asset.write_bytes(b"correct-model")
    docs=tmp_path / "docs"
    docs.mkdir()
    (docs / "turbo-download.json").write_text(json.dumps(dict(repo=checker.MODEL_REPO,revision=checker.MODEL_REVISION,
        files=[dict(name=asset.name,bytes=asset.stat().st_size,sha256=hashlib.sha256(asset.read_bytes()).hexdigest())])))
    monkeypatch.setattr(checker,"ROOT",tmp_path)
    def local_snapshot(repo,**kwargs):
        assert kwargs["local_files_only"] is True
        assert kwargs["revision"] == checker.MODEL_REVISION
        assert kwargs["allow_patterns"] == ["model.bin"]
        return str(model)
    monkeypatch.setitem(sys.modules,"huggingface_hub",SimpleNamespace(snapshot_download=local_snapshot))
    return asset


def test_no_cuda_reports_unsupported_pc_without_downloading(pc_check):
    report=checker.inspect(verify_model=True)
    assert not report["ok"]
    failed=[c for c in report["checks"] if not c["ok"]]
    assert len(failed)==1
    assert failed[0]["name"]=="NVIDIA GPU"
    assert "Intel/AMD" in failed[0]["detail"]


def test_changed_model_checksum_is_rejected(pc_check):
    pc_check.write_bytes(b"changed-model")  # Same size: checksum must catch it.
    report=checker.inspect(verify_model=True)
    model=next(c for c in report["checks"] if c["name"]=="Local Turbo model")
    assert not model["ok"] and "checksum mismatch" in model["detail"]


def test_progress_is_visible_before_a_blocking_check(pc_check,monkeypatch):
    output=[]
    def dependency_probe(*args,**kwargs):
        assert output[-1]=="Checking Dependencies..."
        return subprocess.CompletedProcess(args,0,"Version available\n","")
    monkeypatch.setattr(checker.subprocess,"run",dependency_probe)
    def progress(message,**kwargs):
        assert kwargs["flush"] is True
        output.append(message)
    checker.inspect(progress=progress)
    assert output[0]=="Checking Windows / Python..."
    assert any(line.startswith("[FAIL] NVIDIA GPU:") for line in output)
