"""Local diagnostics and constant-gain listening copies for the frozen comparison."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(ROOT/'model-cache/huggingface')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--long-form', action='store_true', help='Word timestamps, issue clips, and tempo listening export')
    parser.add_argument('--word-timestamps', action='store_true', help='Localize word differences without long-form exports')
    args = parser.parse_args()
    root = (args.run or ROOT / 'benchmarks/results/qwen3-vs-chatterbox/2026-11-18').resolve()
    if not root.is_relative_to((ROOT/'benchmarks/results').resolve()):
        raise ValueError('Expected an isolated benchmark directory.')
    plan = json.loads((root / 'plan.json').read_text(encoding='utf-8'))
    def blocked(*a, **kw):
        raise RuntimeError('Offline evaluation')
    socket.socket.connect = blocked
    import numpy as np
    import soundfile as sf
    import torch
    import librosa
    from scripts.validate_long_form_words import alignment
    from scripts.expressive_delivery_experiment import waveform_metrics
    from app.audio import combine
    from app.config import Settings
    from scripts.legacy_turbo_engine import MODEL_REVISION
    from transformers import WhisperProcessor, WhisperForConditionalGeneration, pipeline
    from transformers.models.whisper.english_normalizer import EnglishTextNormalizer
    from chatterbox.models.voice_encoder import VoiceEncoder
    from safetensors.torch import load_file
    from huggingface_hub import snapshot_download
    torch.set_num_threads(4)
    ve = VoiceEncoder()
    folder = snapshot_download('ResembleAI/chatterbox-turbo', revision=MODEL_REVISION,
        cache_dir=str(Settings().cache_root/'hub'), local_files_only=True, allow_patterns=['ve.safetensors'])
    ve.load_state_dict(load_file(Path(folder)/'ve.safetensors'))
    ve.eval()
    def embed(a, sr):
        a = librosa.resample(a, orig_sr=sr, target_sr=16000)
        with torch.inference_mode():
            return ve.embeds_from_wavs([a], sample_rate=16000)[0]
    def cosine(a,b):
        return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
    ref, sr = sf.read(plan['reference_path'], dtype='float32')
    reference = embed(ref, sr)
    manifest = json.loads((ROOT/'model-cache/validation-asr/download.json').read_text())
    processor = WhisperProcessor.from_pretrained(manifest['snapshot'], local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(manifest['snapshot'], local_files_only=True,
        torch_dtype=torch.float16, attn_implementation='eager').to('cuda').eval()
    normalizer = EnglishTextNormalizer(processor.tokenizer.english_spelling_normalizer)
    def timestamp_differences(decode, chunks, duration):
        """Localize normalized ASR edits; missing words have review windows, not measured timestamps."""
        words, owners = [], []
        for chunk in chunks:
            normalized = normalizer(chunk['text']).split()
            words.extend(normalized)
            owners.extend([chunk['timestamp']]*len(normalized))
        actual = normalizer(decode['transcript']).split()
        timing = [None]*len(actual)
        for tag,a,b,c,d in difflib.SequenceMatcher(a=actual,b=words,autojunk=False).get_opcodes():
            if tag == 'equal':
                timing[a:b] = owners[c:d]
            else:
                nearby = owners[max(0,c-1):min(len(owners),max(c+1,d))]
                starts = [x[0] for x in nearby if x[0] is not None]
                ends = [x[1] for x in nearby if x[1] is not None]
                timing[a:b] = [(min(starts,default=0),max(ends,default=duration))]*(b-a)
        offset, issues = 0, []
        for diff in decode['differences']:
            index = diff['expected_index']+offset
            candidates = timing[max(0,index-1):min(len(timing),index+2)] if diff['operation']=='deletion' else timing[max(0,index):max(0,index)+1]
            candidates = [x for x in candidates if x]
            starts = [x[0] for x in candidates if x[0] is not None]
            ends = [x[1] for x in candidates if x[1] is not None]
            issues.append({**diff,'section_seconds':[min(starts,default=0),max(ends,default=duration)],
                'timestamp_method':'Approximate unprompted Whisper word alignment; omissions use neighboring words.'})
            offset += {'insertion':1,'deletion':-1,'substitution':0}[diff['operation']]
        return issues
    recognizer = pipeline('automatic-speech-recognition', model=model, tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor, device=0, chunk_length_s=30,
        stride_length_s=(4,4), torch_dtype=torch.float16)
    output = root/'diagnostics.json'
    report = json.loads(output.read_text()) if output.exists() else {'asr_repo':manifest['repo'],
        'asr_revision':manifest['revision'], 'expected_text_not_prompted':True, 'takes':{}}
    waves = {}
    for config in plan['configs']:
        for mode in ('main','restart'):
            folder = root/config/mode
            if not (folder/'measurements.json').exists():
                continue
            measure = json.loads((folder/'measurements.json').read_text())
            for take in measure['takes']:
                path = folder/(take['passage']+'.wav')
                key = str(path.relative_to(root)).replace('\\','/')
                assert hashlib.sha256(path.read_bytes()).hexdigest() == take['sha256']
                a, sr = sf.read(path, dtype='float32')
                if key not in report['takes']:
                    print('CHECK', key, flush=True)
                    audio = librosa.resample(a, orig_sr=sr, target_sr=16000)
                    entry = {'waveform':waveform_metrics(a,sr), 'speaker_embedding':embed(a,sr).tolist()}
                    entry['speaker_cosine_to_reference'] = cosine(np.asarray(entry['speaker_embedding']),reference)
                    tick = time.perf_counter()
                    for name, beams in [('greedy',1),('beam',5)]:
                        kwargs = {'return_timestamps':'word'} if (args.long_form or args.word_timestamps) and beams==1 else {}
                        prediction = recognizer({'array':audio,'sampling_rate':16000},
                            generate_kwargs={'do_sample':False,'num_beams':beams,'max_new_tokens':440},**kwargs)
                        transcript = prediction['text']
                        entry[name] = {'transcript':transcript, **alignment(normalizer(take['text']).split(),normalizer(transcript).split())}
                        if kwargs:
                            entry['word_timestamps'] = prediction['chunks']
                    entry['asr_seconds'] = time.perf_counter()-tick
                    if args.long_form or args.word_timestamps:
                        for name in ('greedy','beam'):
                            entry[name]['localized_differences'] = timestamp_differences(entry[name],entry['word_timestamps'],len(a)/sr)
                    report['takes'][key] = entry
                    output.write_text(json.dumps(report,indent=2))
                waves[key] = (a,sr)
    # A single LUFS target across every individual passage and combined master.
    for config in plan['configs']:
        keys = [f'{config}/main/{p["id"]}.wav' for p in plan['passages']]
        if all(k in waves for k in keys):
            assert all(waves[k][1] == 24000 for k in keys)
            master, inserted = combine([waves[k][0] for k in keys], .12)
            path = root/config/'raw_1.00x.wav'
            if not path.exists():
                sf.write(path, master, 24000, subtype='FLOAT')
            existing, _ = sf.read(path,dtype='float32')
            assert np.array_equal(existing, master)
            key = f'{config}/raw_1.00x.wav'
            waves[key] = (master,24000)
            report.setdefault('masters',{})[config] = {'waveform':waveform_metrics(master,24000),
                'inserted_gaps_seconds':inserted, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    metrics = {k:waveform_metrics(a,sr) for k,(a,sr) in waves.items()}
    target = min(-23.,*(m['integrated_lufs']-1-m['sample_peak_dbfs'] for m in metrics.values()))
    report['common_listening_lufs'] = target
    report['listening'] = {}
    listening = root/'listening'
    listening.mkdir(exist_ok=True)
    for key,(a,sr) in waves.items():
        gain = target-metrics[key]['integrated_lufs']
        path = listening/(key.replace('/','__').replace('.wav','_levelmatched.wav'))
        sf.write(path, a*10**(gain/20), sr, subtype='FLOAT')
        report['listening'][key] = {'file':str(path.relative_to(root)).replace('\\','/'), 'gain_db':gain}
    report['restart_checks'] = {}
    for config in plan['configs'] if 'restart_passage' in plan else []:
        keys = [f'{config}/{m}/{plan["restart_passage"]}.wav' for m in ('main','restart')]
        if all(k in waves for k in keys):
            a,b = [waves[k][0] for k in keys]
            ea,eb = [np.array(report['takes'][k]['speaker_embedding']) for k in keys]
            report['restart_checks'][config] = {'sample_identical':bool(np.array_equal(a,b)),
                'speaker_cosine':cosine(ea,eb),'durations_seconds':[len(x)/24000 for x in (a,b)]}
    output.write_text(json.dumps(report,indent=2))
    if args.long_form:
        from app.audio import convert
        config = plan['configs'][0]
        master_key = f'{config}/raw_1.00x.wav'
        master, sr = waves[master_key]
        tempo = root/config/'tempo_1.10x.wav'
        if not tempo.exists():
            convert(root/master_key,tempo,1.1)
        tempo_audio, tempo_sr = sf.read(tempo,dtype='float32')
        tempo_metrics = waveform_metrics(tempo_audio,tempo_sr)
        tempo_gain = min(target-tempo_metrics['integrated_lufs'],-1-tempo_metrics['sample_peak_dbfs'])
        tempo_listening = listening/'qwen06_default_tempo_1.10x_levelmatched.wav'
        sf.write(tempo_listening,tempo_audio*10**(tempo_gain/20),tempo_sr,subtype='FLOAT')
        report['tempo_export'] = {'file':str(tempo.relative_to(root)), 'filter':'FFmpeg atempo=1.1; FLOAT PCM',
            'waveform':tempo_metrics,'listening_file':str(tempo_listening.relative_to(root)),
            'listening_gain_db':tempo_gain,'listening_lufs':tempo_metrics['integrated_lufs']+tempo_gain}
        clips = root/'flagged-clips'
        clips.mkdir(exist_ok=True)
        cursor = 0
        report['sections'] = []
        report['flagged_clips'] = []
        # Reconstruct exact offsets using the same quiet-edge-aware assembly.
        arrays = [waves[f'{config}/main/{p["id"]}.wav'][0] for p in plan['passages']]
        def quiet_edges(a):
            frames = a[:len(a)//240*240].reshape(-1,240)
            audible = np.flatnonzero(np.sqrt(np.mean(frames.astype('float64')**2,axis=1))>=10**(-45/20))
            return (audible[0]/100,(len(frames)-1-audible[-1])/100) if len(audible) else (len(a)/sr,len(a)/sr)
        first_embedding = np.array(report['takes'][f'{config}/main/{plan["passages"][0]["id"]}.wav']['speaker_embedding'])
        for index,passage in enumerate(plan['passages']):
            inserted = 0
            if index:
                _,inserted = combine(arrays[index-1:index+1],.12)
                cursor += round(inserted*sr)
            a = arrays[index]
            key = f'{config}/main/{passage["id"]}.wav'
            entry = report['takes'][key]
            offset = cursor/sr
            section = {'passage':passage['id'],'start_seconds':offset,'end_seconds':(cursor+len(a))/sr,
                'speaker_cosine_to_reference':entry['speaker_cosine_to_reference'],
                'speaker_cosine_to_first':cosine(np.array(entry['speaker_embedding']),first_embedding)}
            if index:
                section['speaker_cosine_to_previous'] = cosine(np.array(entry['speaker_embedding']),np.array(report['takes'][f'{config}/main/{plan["passages"][index-1]["id"]}.wav']['speaker_embedding']))
                section['join_quiet_seconds_at_minus45_dbfs'] = quiet_edges(arrays[index-1])[1]+quiet_edges(a)[0]+inserted
            full_scale = np.abs(a)>=1
            edges = np.diff(np.r_[False,full_scale,False].astype(int))
            starts,ends = np.flatnonzero(edges==1),np.flatnonzero(edges==-1)
            section['full_scale_sample_count'] = int(full_scale.sum())
            section['longest_full_scale_run_samples'] = int(max(ends-starts,default=0))
            report['sections'].append(section)
            ranges = []
            if section.get('join_quiet_seconds_at_minus45_dbfs',0)>.8:
                ranges.append((max(0,offset-3),min(len(master)/sr,offset+3)))
                section['join_review_flag'] = 'Quiet interval exceeds 0.8 seconds; listening needed to judge transition.'
            if section['longest_full_scale_run_samples']>=8:
                at = float(starts[np.argmax(ends-starts)])/sr+offset
                ranges.append((max(0,at-2),min(len(master)/sr,at+2)))
                section['saturation_review_seconds'] = at
            for decode in ('greedy','beam'):
                for issue in entry[decode]['localized_differences']:
                    start,end = issue['section_seconds']
                    issue['master_seconds'] = [offset+start,offset+end]
                    ranges.append((max(0,offset+start-2),min(len(master)/sr,offset+end+2)))
            merged = []
            for start,end in sorted(ranges):
                if merged and start<=merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1],end)
                else:
                    merged.append([start,end])
            gain = report['listening'][master_key]['gain_db']
            for j,(start,end) in enumerate(merged,1):
                path = clips/f'{passage["id"]}_issue_{j:02}.wav'
                clip = master[round(start*sr):round(end*sr)]*10**(gain/20)
                sf.write(path,clip,sr,subtype='FLOAT')
                report['flagged_clips'].append({'passage':passage['id'],'file':str(path.relative_to(root)),
                    'master_seconds':[start,end],'gain_db':gain})
            cursor += len(a)
        assert cursor == len(master)
        report['long_form_duration_in_target'] = 300<=len(master)/sr<=600
        output.write_text(json.dumps(report,indent=2))
    print('Diagnostics saved',flush=True)


if __name__ == '__main__':
    main()
