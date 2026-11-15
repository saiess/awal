"""Six bounded sentence-level calls, preserving unaffected original samples.

Isolated experiment only. Seed 1234, no retries, no script rewriting or app use.
"""
import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
from app.audio import combine,write_raw
from app.config import Settings,CODE_REVISION,MODEL_REVISION
from app.projects import file_hash
from app.segmentation import sentences
from app.tts.engine import TurboEngine
from scripts.expressive_delivery_experiment import waveform_metrics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();src=args.source.resolve();out=args.output.resolve()
    allowed=(ROOT/'benchmarks/results').resolve()
    assert src.is_relative_to(allowed) and out.is_relative_to(allowed) and src!=out
    out.mkdir(parents=True,exist_ok=False)
    old=json.loads((src/'measurements.json').read_text(encoding='utf-8'))
    config=old['configurations'][0];settings=Settings()
    assert old['code_revision']==CODE_REVISION and old['model_revision']==MODEL_REVISION
    params=dict(config['parameters']);assert params['temperature']==.9 and params['seed']==1234
    reference=settings.data_root/old['reference']['path']
    assert file_hash(reference)==old['reference']['sha256']
    protected={str(f.relative_to(ROOT)):file_hash(f)
               for folder in ('data/projects','data/narrators','app','frontend/src','benchmarks/results/expressive-delivery/C-long-form-2026-11-15','benchmarks/results/expressive-delivery/C-section-repair-2026-11-15')
               for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    import httpx
    try:
        health=httpx.get('http://127.0.0.1:8000/api/health',trust_env=False,timeout=4).json()
        assert not health['busy'] and not health['engine_loaded'],'GPU in use; no overlapping generation.'
    except httpx.ConnectError:
        pass
    connect=socket.socket.connect
    def offline(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6):raise RuntimeError('Network disabled.')
        return connect(sock,address)
    socket.socket.connect=offline
    report={'status':'running','source':str(src.relative_to(ROOT)),'parameters':params,
            'reference':old['reference'],'code_revision':CODE_REVISION,'model_revision':MODEL_REVISION,
            'maximum_generation_calls':6,'retries':0,'protected_sha256':protected,'sections':[]}
    def save():
        (out/'boundary-measurements.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    save()
    import numpy as np
    import soundfile as sf
    # Midpoints of >=60 ms low-RMS runs, located at natural sentence boundaries.
    # No cuts are made within spoken words. Saved text/ASR and quiet measurements
    # explain these experiment-specific coordinates; this is not an auto-editor.
    plans={6:[('original',[1,2,3],0,17.1125),('generate',[4],None,None),('generate',[5],None,None)],
           9:[('generate',[1],None,None),('generate',[2],None,None),('original',[3],5.9025,11.6825),
              ('generate',[4],None,None),('original',[5],16.9725,18.85),('generate',[6],None,None)]}
    try:
        engine=TurboEngine(settings);tick=time.perf_counter()
        print('Preparing pinned Turbo runtime...',flush=True)
        engine.prepare_runtime();engine.load();report['prepare_and_load_seconds']=time.perf_counter()-tick
        trace={};inference=engine.model.t3.inference_turbo
        def traced(*a,**kw):
            tokens=inference(*a,**kw);trace['speech_tokens']=int(tokens.numel());return tokens
        engine.model.t3.inference_turbo=traced
        for index,plan in plans.items():
            s=config['sections'][index-1];parts=list(sentences(s['text']))
            assert ' '.join(parts)==s['text']
            assert ' '.join(' '.join(parts[i-1] for i in ids) for _,ids,_,_ in plan)==s['text']
            original,sr=sf.read(src/s['file'],dtype='float32');assert file_hash(src/s['file'])==s['sha256']
            record={'section':index,'source_text':s['text'],'original_file':s['file'],'parts':[]}
            report['sections'].append(record);arrays=[]
            for part_id,(kind,ids,start,end) in enumerate(plan,1):
                text=' '.join(parts[i-1] for i in ids);entry={'part':part_id,'kind':kind,'sentences':ids,'text':text}
                record['parts'].append(entry);save()
                dest=out/f'section-{index:02}-part-{part_id:02}-{kind}_raw.wav'
                if kind=='original':
                    first=round(start*sr);last=round(end*sr)
                    audio=original[first:last].copy()
                    quiet={}
                    for label,sample in (('start',first),('end',last)):
                        if sample not in (0,len(original)):
                            region=original[sample-240:sample+240]
                            rms=float(np.sqrt(np.mean(region.astype(float)**2)))
                            assert rms<10**(-45/20)
                            quiet[label]=20*np.log10(max(rms,1e-12))
                    entry.update(source_start_sample=first,source_end_sample=last,quiet_cut_rms_dbfs=quiet)
                else:
                    print(f'Generating section {index}, sentence {ids[0]}, seed 1234',flush=True)
                    result=engine.synthesize(text,reference,params);audio=result.samples
                    entry.update(seed=1234,**result.metrics,speech_tokens=trace['speech_tokens'])
                    assert trace['speech_tokens']<1000
                info=write_raw(dest,audio,sr);entry.update(file=dest.name,**info)
                if kind=='original':
                    decoded,_=sf.read(dest,dtype='float32');assert np.array_equal(decoded,original[first:last])
                    entry['original_samples_identical']=True
                arrays.append(audio);save()
            assembly,inserted=combine(arrays,.12)
            dest=out/f'section-{index:02}-sentence-boundaries_raw.wav'
            info=write_raw(dest,assembly,sr)
            record.update(file=dest.name,**info,inserted_gap_seconds=inserted,waveform=waveform_metrics(assembly,sr))
            # Record join locations and the actual low-level quiet interval around each cut.
            joins=[]
            for i in range(1,len(arrays)):
                prefix,_=combine(arrays[:i],.12);through,_=combine(arrays[:i+1],.12)
                left_end=len(prefix)/sr;right_start=(len(through)-len(arrays[i]))/sr
                def edge_quiet(a):
                    active=np.flatnonzero(np.abs(a)>=10**(-45/20))
                    return int(active[0])/sr if len(active) else len(a)/sr
                joins.append({'left_part':i,'right_part':i+1,'left_end_seconds':left_end,'right_start_seconds':right_start,
                              'combined_quiet_seconds':edge_quiet(arrays[i-1][::-1])+right_start-left_end+edge_quiet(arrays[i])})
            record['joins']=joins;save()
        report['status']='completed'
    except BaseException as error:
        report['status']='failed';report['error']=repr(error);raise
    finally:
        report['protected_files_unchanged']=all(file_hash(ROOT/f)==h for f,h in protected.items());save()
    assert report['protected_files_unchanged']
    assert sum(p['kind']=='generate' for s in report['sections'] for p in s['parts'])==6
    print('Six sentence calls complete; all original recordings and retained samples preserved.',flush=True)


if __name__=='__main__':main()
