from uuid import uuid4

import pytest

from conftest import create_project, reference_bytes


@pytest.mark.parametrize('script', ['', '  ', '!', 'x'*100001], ids=['empty','whitespace','punctuation','oversized'])
def test_invalid_script_rejected(setup, script):
    c, app, engine, n = setup
    response = c.post('/api/projects', json={'title':'Test','script':script,'narrator_id':n['id']})
    assert response.status_code == 422


def test_ids_origin_filename_and_narrator_validation(setup):
    c, app, e, n = setup
    assert c.get('/api/projects/not-a-uuid').status_code == 422
    assert c.get('/api/projects/'+str(uuid4())).status_code == 404
    assert c.post('/api/projects', json={'title':'X','script':'Text.','narrator_id':str(uuid4())}).status_code == 404
    assert c.post('/api/segment', json={'script':'Valid text.'}, headers={'Origin':'https://example.com'}).status_code == 403
    assert c.get('/api/health', headers={'Host':'evil.example'}).status_code == 400
    assert c.get('/').status_code == 200
    html = c.get('/').text
    import re
    script = re.search(r'src="(/static/ui/assets/[^\"]+\.js)"', html)
    assert script is not None
    assert c.get(script.group(1)).status_code == 200
    assert c.get('/api/health').json()['engine_loaded'] is False


@pytest.mark.parametrize('filename,content_type,data,rights,expected', [
    ('reference.wav','audio/wav',b'corrupt','true',422),
    ('reference.wav','audio/wav',b'anything','false',403),
    ('../reference.wav','audio/wav',b'anything','true',422),
    ('reference.txt','text/plain',b'anything','true',415),
    ('short.wav','audio/wav',reference_bytes(1),'true',422),
    ('large.wav','audio/wav',b'x'*(15*1024*1024+1),'true',413),
], ids=['corrupt','no-consent','traversal','wrong-type','too-short','too-large'])
def test_reference_upload_validation(setup, filename, content_type, data, rights, expected):
    c, app, e, n = setup
    r = c.post('/api/narrators', data={'label':'Voice','rights_confirmed':rights,'reference_transcript':'The exact words in the recording.'}, files={'reference_audio':(filename,data,content_type)})
    assert r.status_code == expected, r.text
    assert app.state.store.narrator()['id'] == n['id']


def test_valid_reference_replacement_affects_new_projects_only(setup):
    c, app, e, n = setup
    old = create_project(c,n)
    r=c.post('/api/narrators',data={'label':'New voice','rights_confirmed':'true','reference_transcript':'The exact words in the recording.'},files={'reference_audio':('ref.wav',reference_bytes(),'audio/wav')})
    assert r.status_code == 201, r.text
    assert c.get(f"/api/projects/{old['id']}").json()['narrator']['id'] == n['id']
    assert c.get('/api/narrators').json()[0]['id'] == r.json()['id']
    assert c.get(f"/api/narrators/{n['id']}/reference").status_code == 200
