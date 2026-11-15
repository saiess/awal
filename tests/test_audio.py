import io
import json
import zipfile
from uuid import uuid4

import numpy as np
import pytest
import soundfile as sf

from app.audio import combine, finish_master, smooth_joins
from app.projects import file_hash
from conftest import create_project, finish


def test_boundary_gaps_do_not_double_existing_silence():
    voice=np.ones(100,dtype=np.float32)*.1
    zeros=np.zeros(2400,dtype=np.float32)
    a=np.r_[voice,zeros];b=np.r_[zeros,voice]
    combined,added=combine([a,b],.12)
    assert added==0 and len(combined)==len(a)+len(b)
    combined,added=combine([voice,voice],.12)
    assert added==.12 and len(combined)==200+2880


def test_exports_speed_order_mp3_zip_and_preserved_raws(setup):
    c, app, e, n=setup
    p=create_project(c,n)
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    p=app.state.store.read(p['id'])
    old={s['id']:file_hash(app.state.store.path(s['audio_path'])) for s in p['segments']}
    def export(**options):
        r=c.post(f"/api/projects/{p['id']}/exports",json=options)
        assert r.status_code==201,r.text
        record=r.json();url=f"/api/projects/{p['id']}/exports/{record['id']}/download"
        return record,c.get(url)
    raw,response=export(processed=False,speed=1.1,gap_seconds=0)
    decoded,sr=sf.read(io.BytesIO(response.content),dtype='float32')
    expected=np.concatenate([sf.read(app.state.store.path(s['audio_path']),dtype='float32')[0] for s in p['segments']])
    assert np.array_equal(decoded,expected) and raw['effective_speed']==1.0
    processed,response=export(processed=True,speed=1.1,gap_seconds=.12)
    assert abs(processed['duration_seconds']-(3+.24)/1.1)<.1
    mp3,response=export(format='mp3',processed=True,speed=1.1)
    a,sr=sf.read(io.BytesIO(response.content))
    assert sr==24000 and abs(len(a)/sr-mp3['duration_seconds'])<.02
    archive,response=export(include_segments=True,processed=False,segment_ids=[p['segments'][2]['id'],p['segments'][0]['id']],gap_seconds=0)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert {'master.wav','section-001.wav','section-002.wav','sections.json'}==set(z.namelist())
        snapshot=json.loads(z.read('sections.json'))
        assert snapshot['sections'][0]['id']==p['segments'][0]['id']
        assert snapshot['sections'][1]['id']==p['segments'][2]['id']
    enhanced,response=export(enhance=True,processed=True)
    a,sr=sf.read(io.BytesIO(response.content))
    assert np.max(np.abs(a))<=10**(-1/20)+1e-6
    assert all(file_hash(app.state.store.path(s['audio_path']))==old[s['id']] for s in p['segments'])


def test_incomplete_stale_and_unknown_sections_reject_export(setup):
    c,app,e,n=setup;p=create_project(c,n)
    assert c.post(f"/api/projects/{p['id']}/exports",json={}).status_code==409
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    c.patch(f"/api/projects/{p['id']}/segments/{p['segments'][0]['id']}",json={'text':'Changed text.'})
    assert c.post(f"/api/projects/{p['id']}/exports",json={}).status_code==409
    assert c.post(f"/api/projects/{p['id']}/exports",json={'segment_ids':[str(uuid4())]}).status_code==404
    for speed in [.1,2.1,'NaN']:
        assert c.post(f"/api/projects/{p['id']}/exports",json={'speed':speed}).status_code==422


def test_join_cleanup_preserves_speech_interior_pauses_and_inputs():
    voice = np.full(12000, .12, dtype=np.float32)
    quiet = np.zeros(24000, dtype=np.float32)
    # The long interior pause must stay; only the two edges at the join shorten.
    left = np.r_[voice, quiet, voice, quiet]
    right = np.r_[quiet, voice]
    originals = [left.copy(), right.copy()]
    cleaned, info = smooth_joins([left, right])
    assert info['trimmed_seconds'] == pytest.approx(1.7)
    assert np.array_equal(cleaned[0][:len(voice)*2 + len(quiet)], left[:len(voice)*2 + len(quiet)])
    assert np.array_equal(cleaned[1][3600:], voice)
    assert all(np.array_equal(a,b) for a,b in zip([left,right], originals))
    # Short quiet and an entirely quiet section are not trimmed.
    soft = np.sin(np.arange(24000)/20).astype(np.float32)*.0001
    short = np.r_[voice, np.zeros(4800,dtype=np.float32)]
    same, info = smooth_joins([short, soft])
    assert info['trimmed_seconds'] == 0
    assert [len(a) for a in same] == [len(short),len(soft)]
    # A hard edge fades to zero over only 3 ms, without overlapping words.
    faded, _ = smooth_joins([voice,voice])
    assert faded[0][-1] == 0 and faded[1][0] == 0
    assert np.array_equal(faded[0][:-72],voice[:-72])
    assert np.array_equal(faded[1][72:],voice[72:])


@pytest.mark.parametrize('format',['wav','mp3'])
def test_processed_export_peak_protection_checks_decoded_audio(tmp_path,format):
    # A loud square wave exercises both excessive source peaks and MP3 overshoot.
    a=(1.6*np.sign(np.sin(2*np.pi*311*np.arange(48000)/24000))).astype(np.float32)
    source=tmp_path/'working.wav';sf.write(source,a,24000,subtype='FLOAT')
    decoded,sr,info=finish_master(source,tmp_path/f'master.{format}',format,True)
    assert sr==24000 and np.max(np.abs(decoded))<=10**(-1/20)+1e-6
    assert info['gain_db']<0 and info['decoded_sample_peak_dbfs']<=-1+1e-5


def test_export_cleanup_is_processed_only_and_preserves_raws(setup):
    c,app,e,n=setup
    p=create_project(c,n,'First.\n\nSecond.')
    finish(c,c.post(f"/api/projects/{p['id']}/generate",json={}))
    p=app.state.store.read(p['id'])
    voice=np.full(12000,.1,dtype=np.float32);quiet=np.zeros(24000,dtype=np.float32)
    arrays=[np.r_[voice,quiet],np.r_[quiet,voice]]
    for s,a in zip(p['segments'],arrays): sf.write(app.state.store.path(s['audio_path']),a,24000,subtype='FLOAT')
    hashes=[file_hash(app.state.store.path(s['audio_path'])) for s in p['segments']]
    for processed in (False,True):
        r=c.post(f"/api/projects/{p['id']}/exports",json={'processed':processed,'speed':1,'gap_seconds':0})
        assert r.status_code==201,r.text
        record=r.json()
        a,_=sf.read(app.state.store.path(record['audio_path']),dtype='float32')
        if processed:
            assert record['join_processing']['trimmed_seconds']==pytest.approx(1.7)
            assert record['duration_seconds']==pytest.approx(1.3)
            assert record['peak_protection']['gain_db']==0
        else:
            assert np.array_equal(a,np.concatenate(arrays))
            assert record['join_processing'] is None and record['peak_protection'] is None
    assert hashes==[file_hash(app.state.store.path(s['audio_path'])) for s in p['segments']]
