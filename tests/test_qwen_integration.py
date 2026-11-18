import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.audio import trim_trailing_quiet
from app.config import ENGINE_ID
from app.projects import Store, file_hash
from conftest import create_project, finish


def test_override_preserves_script_source_and_generation_versions(setup):
    c,app,e,n=setup
    p=create_project(c,n,'There are 17,400 files.')
    s=p['segments'][0]
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    old=app.state.store.read(p['id'])['segments'][0]
    corrected='There are seventeen thousand four hundred files.'
    r=c.patch(f"/api/projects/{p['id']}/segments/{s['id']}",json={'inference_text':corrected})
    assert r.status_code==200
    assert r.json()['script']==p['script'] and r.json()['segments'][0]['text']==s['text']
    assert r.json()['segments'][0]['inference_text']==corrected
    assert c.post(f"/api/projects/{p['id']}/exports",json={}).status_code==409
    finish(c,c.post(f"/api/projects/{p['id']}/segments/{s['id']}/regenerate",json={}))
    saved=app.state.store.read(p['id'])['segments'][0]
    assert saved['generated_text']==corrected and len(saved['versions'])==2
    assert saved['versions'][0]['inference_text']==s['text']
    assert saved['versions'][1]['inference_text']==corrected
    assert saved['attempts'][-1]['parameters']['reference_text']==n['reference_transcript']
    assert saved['versions'][-1]['engine_id']==ENGINE_ID
    assert file_hash(app.state.store.path(old['audio_path']))==old['sha256']
    assert c.patch(f"/api/projects/{p['id']}/segments/{s['id']}",json={'text':'Overwrite source'}).status_code==422
    reset=c.patch(f"/api/projects/{p['id']}/segments/{s['id']}",json={'inference_text':None})
    assert reset.json()['segments'][0]['inference_text'] is None


def test_original_script_preserves_exact_whitespace(setup):
    c,app,e,n=setup
    script='  A complete sentence.\r\n\r\nAnother sentence.  '
    p=create_project(c,n,script)
    assert p['script']==script
    assert [s['text'] for s in p['segments']]==['A complete sentence.','Another sentence.']


def test_legacy_audio_exports_even_after_stale_edit_but_cannot_generate(setup):
    c,app,e,n=setup;p=create_project(c,n,'An old completed recording.')
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    p=app.state.store.read(p['id']);p.update(schema_version=1,engine_id='chatterbox-turbo',engine_revision='legacy')
    p['segments'][0].update(stale=True,status='pending')
    app.state.store.save(p);s=p['segments'][0];calls=e.calls
    assert c.get(f"/api/projects/{p['id']}/segments/{s['id']}/audio").status_code==200
    assert c.post(f"/api/projects/{p['id']}/exports",json={'processed':False}).status_code==201
    for endpoint in ('generate',f"segments/{s['id']}/regenerate"):
        assert c.post(f"/api/projects/{p['id']}/{endpoint}",json={}).status_code==409
    assert e.calls==calls and not app.state.jobs.gate.locked()
    assert c.patch(f"/api/projects/{p['id']}/segments/{s['id']}",json={'inference_text':'New'}).status_code==422
    assert app.state.store.read(p['id'])['engine_id']=='chatterbox-turbo'


def test_transcript_sidecar_preserves_profile_and_snapshots(setup):
    c,app,e,n=setup;store=app.state.store
    profile=store.path(f"narrators/{n['id']}/profile.json");before=profile.read_bytes()
    p=create_project(c,n)
    response=c.patch(f"/api/narrators/{n['id']}/transcript",json={'transcript':'A newly confirmed transcript.'})
    assert response.status_code==200 and profile.read_bytes()==before
    assert store.read(p['id'])['narrator']['reference_transcript']==n['reference_transcript']
    newer=create_project(c,n)
    assert newer['narrator']['reference_transcript']=='A newly confirmed transcript.'
    restarted=Store(store.settings)
    assert restarted.read(newer['id'])['narrator']==newer['narrator']
    assert restarted.narrator(n['id'])['reference_transcript']=='A newly confirmed transcript.'


def test_missing_transcript_prevents_incomplete_qwen_project(setup):
    c,app,e,n=setup;store=app.state.store
    profile=store.path(f"narrators/{n['id']}/profile.json")
    data=json.loads(profile.read_text());data.pop('reference_transcript');profile.write_text(json.dumps(data))
    r=c.post('/api/projects',json={'title':'Missing transcript','script':'A sentence.','narrator_id':n['id']})
    assert r.status_code==422 and 'transcript' in r.json()['detail']
    assert not store.list_projects()


def test_trim_only_suffix_preserves_internal_pause_and_samples():
    voice=np.ones(12000,dtype='float32')*.1
    a=np.r_[voice,np.zeros(24000,dtype='float32'),voice,np.zeros(5*24000,dtype='float32')]
    saved=a.copy();trimmed,info=trim_trailing_quiet([a])
    assert np.array_equal(trimmed[0],a[:48000+8400])
    assert np.array_equal(a,saved) and info['sections'][0]['removed_seconds']==pytest.approx(4.65)
    soft=np.ones(24000,dtype='float32')*.0001
    unchanged,_=trim_trailing_quiet([soft])
    assert np.array_equal(unchanged[0],soft)


def test_gpu_headroom_guard_rejects_before_loading_weights(monkeypatch):
    import sys
    from app.tts.engine import QwenEngine
    from app.config import Settings
    e=QwenEngine(Settings());e.prepare_runtime=lambda:None
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(cuda=SimpleNamespace(
        is_available=lambda:True,mem_get_info=lambda:(5*1024**3,8*1024**3))))
    with pytest.raises(RuntimeError,match='6 GiB'):
        e.load()
    assert not e.loaded


def test_qwen_export_trim_is_processed_only_and_never_changes_raw(setup):
    import io
    import soundfile as sf
    from app.tts.engine import AudioResult
    c,app,e,n=setup
    voice=np.sin(np.arange(12000,dtype='float32')*.1)*.1
    raw=np.r_[voice,np.zeros(24000,dtype='float32'),voice,np.zeros(120000,dtype='float32')]
    e.synthesize=lambda *args:AudioResult(raw,24000,{})
    p=create_project(c,n,'A complete section.')
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    saved=app.state.store.read(p['id'])['segments'][0]
    for processed in (False,True):
        r=c.post(f"/api/projects/{p['id']}/exports",json={'processed':processed,'trim_trailing_silence':True,'speed':1,'gap_seconds':0})
        assert r.status_code==201,r.text
        record=r.json();response=c.get(f"/api/projects/{p['id']}/exports/{record['id']}/download")
        result,_=sf.read(io.BytesIO(response.content),dtype='float32')
        if processed:
            info=record['join_processing']['sections'][0]
            assert info['removed_samples']>100000 and np.array_equal(result,raw[:info['retained_samples']])
        else:
            assert np.array_equal(result,raw) and record['join_processing'] is None
        assert file_hash(app.state.store.path(saved['audio_path']))==saved['sha256']


def test_qwen_code_checksum_rejects_changed_source_and_accepts_windows_newlines(tmp_path,monkeypatch):
    import hashlib
    import app.tts.engine as engine
    package=tmp_path/'package';package.mkdir()
    source=package/'model.py';source.write_bytes(b'value = 1\r\n')
    docs=tmp_path/'docs';docs.mkdir()
    (docs/'qwen-download.json').write_text(json.dumps({'code_files':{'model.py':hashlib.sha256(b'value = 1\n').hexdigest()}}))
    monkeypatch.setattr(engine,'ROOT',tmp_path)
    monkeypatch.setattr(engine.md,'distribution',lambda _:SimpleNamespace(version='0.1.1',locate_file=lambda _:package))
    engine.verify_code()
    source.write_bytes(b'value = 2\n')
    with pytest.raises(RuntimeError,match='code checksum mismatch'):
        engine.verify_code()
