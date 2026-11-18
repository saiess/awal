"""Local diagnostics and constant-gain listening copies for the frozen comparison."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(ROOT/'model-cache/huggingface')


def main():
    root = ROOT / 'benchmarks/results/qwen3-vs-chatterbox/2026-11-18'
    plan = json.loads((root / 'plan.json').read_text())
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
    from app.config import Settings, MODEL_REVISION
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
                    for name, beams in [('greedy',1),('beam',5)]:
                        prediction = recognizer({'array':audio,'sampling_rate':16000},
                            generate_kwargs={'do_sample':False,'num_beams':beams,'max_new_tokens':440})['text']
                        entry[name] = {'transcript':prediction, **alignment(normalizer(take['text']).split(),normalizer(prediction).split())}
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
    for config in plan['configs']:
        keys = [f'{config}/{m}/{plan["restart_passage"]}.wav' for m in ('main','restart')]
        if all(k in waves for k in keys):
            a,b = [waves[k][0] for k in keys]
            ea,eb = [np.array(report['takes'][k]['speaker_embedding']) for k in keys]
            report['restart_checks'][config] = {'sample_identical':bool(np.array_equal(a,b)),
                'speaker_cosine':cosine(ea,eb),'durations_seconds':[len(x)/24000 for x in (a,b)]}
    output.write_text(json.dumps(report,indent=2))
    print('Diagnostics saved',flush=True)


if __name__ == '__main__':
    main()
