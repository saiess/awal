import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.projects import Store, atomic_json, file_hash, safe_path
from conftest import FakeEngine, create_project, finish


def test_only_target_changes_and_failed_regeneration_preserves_audio(setup):
    client, app, engine, narrator = setup
    p = create_project(client, narrator)
    assert finish(client, client.post(f"/api/projects/{p['id']}/generate", json={}))['status'] == 'ready'
    p = client.get(f"/api/projects/{p['id']}").json()
    before = {s['id']: (s['audio_path'], file_hash(app.state.store.path(s['audio_path']))) for s in p['segments']}
    middle = p['segments'][1]['id']
    changed = client.patch(f"/api/projects/{p['id']}/segments/{middle}", json={"text": "The revised middle section."}).json()
    assert changed['segments'][1]['stale']
    assert changed['segments'][1]['audio_path'] == before[middle][0]
    assert finish(client, client.post(f"/api/projects/{p['id']}/segments/{middle}/regenerate", json={}))['status'] == 'ready'
    latest = client.get(f"/api/projects/{p['id']}").json()
    for s in latest['segments']:
        if s['id'] == middle:
            assert s['audio_path'] != before[middle][0]
        else:
            assert (s['audio_path'], file_hash(app.state.store.path(s['audio_path']))) == before[s['id']]
    good = latest['segments'][1]
    engine.fail = True
    assert finish(client, client.post(f"/api/projects/{p['id']}/segments/{middle}/regenerate", json={}))['status'] == 'failed'
    failed = client.get(f"/api/projects/{p['id']}").json()['segments'][1]
    assert failed['status'] == 'failed' and failed['stale']
    assert failed['audio_path'] == good['audio_path']
    assert file_hash(app.state.store.path(failed['audio_path'])) == good['sha256']
    assert client.get(f"/api/projects/{p['id']}/segments/{middle}/audio").status_code == 200


def test_restart_recovery_retains_good_audio_and_narrator_snapshot(setup, tmp_path):
    client, app, engine, narrator = setup
    p = create_project(client, narrator)
    finish(client, client.post(f"/api/projects/{p['id']}/generate", json={}))
    store = app.state.store
    p = store.read(p['id'])
    old_reference = p['narrator']['reference_sha256']
    replacement = tmp_path/'new.wav'
    replacement.write_bytes(store.path(narrator['reference_audio_relative_path']).read_bytes())
    store.add_narrator('New profile', replacement, {'rights_confirmed': True})
    p['segments'][1]['status'] = 'generating'
    store.save(p)
    reopened = Store(store.settings)
    reopened.recover()
    restored = reopened.read(p['id'])
    assert restored['segments'][1]['status'] == 'pending'
    assert restored['segments'][1]['audio_path'] == p['segments'][1]['audio_path']
    assert restored['narrator']['reference_sha256'] == old_reference
    assert restored['narrator']['id'] != store.narrator()['id']
    assert all(store.path(s['audio_path']).is_file() for s in restored['segments'])


def test_second_app_instance_cannot_recover_another_running_apps_files(setup):
    c, app, e, n = setup
    second = create_app(app.state.store.settings, FakeEngine())
    with pytest.raises(RuntimeError, match='already using this data folder'):
        with TestClient(second, base_url='http://127.0.0.1'):
            pass


def test_atomic_write_failure_keeps_old_manifest(tmp_path, monkeypatch):
    import app.projects as projects
    path = tmp_path/'project.json'
    atomic_json(path, {'valid': True})
    def broken(*args): raise OSError('simulated disk failure')
    monkeypatch.setattr(projects.os, 'replace', broken)
    with pytest.raises(OSError): atomic_json(path, {'valid': False})
    assert json.loads(path.read_text()) == {'valid': True}
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('path', ['../outside.wav', 'C:\\outside.wav', 'projects/../../outside.wav'])
def test_safe_paths_reject_traversal(tmp_path, path):
    with pytest.raises(ValueError): safe_path(tmp_path, path)
