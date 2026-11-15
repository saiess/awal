import threading

import pytest

from app.projects import file_hash
from conftest import create_project, finish


def test_second_generation_and_edit_return_busy_without_blocking_health(setup):
    c, app, e, narrator = setup
    p = create_project(c, narrator)
    e.entered, e.release = threading.Event(), threading.Event()
    first = c.post(f"/api/projects/{p['id']}/generate", json={})
    try:
        assert e.entered.wait(5)
        assert c.post(f"/api/projects/{p['id']}/generate", json={}).status_code == 409
        assert c.patch(f"/api/projects/{p['id']}/segments/{p['segments'][0]['id']}", json={'text':'Changed'}).status_code == 409
        health = c.get('/api/health').json()
        assert health['busy'] and health['active_job']['id'] == first.json()['id']
    finally: e.release.set()
    assert finish(c, first)['status'] == 'ready'


@pytest.mark.parametrize('malformed', ['nan', 'silent', 'rate'])
def test_invalid_engine_output_never_replaces_good_file(setup, malformed):
    c, app, e, n = setup
    p = create_project(c, n, 'One valid section.')
    finish(c, c.post(f"/api/projects/{p['id']}/generate", json={}))
    good = app.state.store.read(p['id'])['segments'][0]
    e.malformed = malformed
    job = finish(c, c.post(f"/api/projects/{p['id']}/segments/{good['id']}/regenerate", json={}))
    assert job['status'] == 'failed'
    s = app.state.store.read(p['id'])['segments'][0]
    assert s['audio_path'] == good['audio_path'] and s['sha256'] == good['sha256']
    assert file_hash(app.state.store.path(s['audio_path'])) == good['sha256']


def test_shutdown_finishes_current_section_and_leaves_rest_resumable(setup):
    c, app, e, n = setup
    p = create_project(c, n)
    e.entered, e.release = threading.Event(), threading.Event()
    first = c.post(f"/api/projects/{p['id']}/generate", json={})
    assert e.entered.wait(5)
    app.state.jobs.stop.set()
    e.release.set()
    job = finish(c, first)
    assert job['status'] == 'interrupted'
    s = app.state.store.read(p['id'])['segments']
    assert s[0]['status'] == 'ready' and s[0]['audio_path']
    assert all(x['status'] == 'pending' for x in s[1:])


def test_model_initialization_failure_is_visible_and_releases_gate(setup):
    c, app, e, n = setup
    p = create_project(c, n)
    def no_cuda(): raise RuntimeError('NVIDIA CUDA is unavailable.')
    e.load = no_cuda
    job = finish(c, c.post(f"/api/projects/{p['id']}/generate", json={}))
    assert job['status'] == 'failed' and 'CUDA' in job['error']
    assert not app.state.jobs.gate.locked()


def test_retries_use_new_recorded_seeds_without_changing_narrator_or_old_audio(setup):
    c,app,e,n=setup
    captured=[]
    synthesize=e.synthesize
    def capture(text,reference,options):
        captured.append(dict(options))
        return synthesize(text,reference,options)
    e.synthesize=capture
    p=create_project(c,n,'One section.')
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    original=app.state.store.read(p['id'])['segments'][0]
    assert captured[-1]['seed']==n['engine_parameters']['seed']
    route=f"/api/projects/{p['id']}/segments/{original['id']}/regenerate"
    e.fail=True
    assert finish(c,c.post(route,json={}))['status']=='failed'
    failed=app.state.store.read(p['id'])['segments'][0]
    assert failed['last_attempt_seed']==captured[-1]['seed']!=captured[0]['seed']
    assert failed['generation_parameters']==captured[0]
    e.fail=False
    assert finish(c,c.post(route,json={}))['status']=='ready'
    updated=app.state.store.read(p['id'])['segments'][0]
    assert updated['generation_parameters']==captured[-1]
    assert updated['last_attempt_seed']!=failed['last_attempt_seed']
    assert app.state.store.narrator(n['id'])['engine_parameters']==n['engine_parameters']
    assert file_hash(app.state.store.path(original['audio_path']))==original['sha256']
