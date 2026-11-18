"""Bounded, offline comparison only; never imported by Awal."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import socket
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for key in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY'):
    os.environ[key] = '1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', choices=['chatterbox_C', 'qwen06_default', 'qwen06_fulltext'], required=True)
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    root = ROOT / 'benchmarks/results/qwen3-vs-chatterbox/2026-11-18'
    plan = json.loads((root / 'plan.json').read_text())
    reference = Path(plan['reference_path'])
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == plan['reference_sha256']
    try:
        health = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).read())
    except OSError:
        health = None
    if health and (health.get('busy') or health.get('active_job')):
        raise RuntimeError('Awal is generating; do not compete with a production job.')
    out = root / args.config / ('restart' if args.restart else 'main')
    out.mkdir(parents=True, exist_ok=False)
    def blocked(*a, **kw):
        raise RuntimeError('Network disabled during benchmark inference')
    socket.socket.connect = blocked
    socket.create_connection = blocked
    import numpy as np
    import soundfile as sf
    import torch
    torch.set_num_threads(4)
    torch.cuda.init()
    if torch.cuda.mem_get_info()[0] < 6*1024**3:
        raise RuntimeError('Less than 6 GiB GPU memory free; preserve production workloads.')
    result = {'config': args.config, 'restart': args.restart, 'offline_socket_guard': True,
              'gpu': torch.cuda.get_device_name(), 'takes': [], 'status': 'started'}
    result['gpu_total_bytes'] = torch.cuda.get_device_properties(0).total_memory
    result['gpu_free_before_load_bytes'] = torch.cuda.mem_get_info()[0]
    def save():
        (out / 'measurements.json').write_text(json.dumps(result, indent=2))
    save()
    try:
        started = time.perf_counter()
        if args.config == 'chatterbox_C':
            from app.config import Settings
            from app.tts.engine import TurboEngine
            engine = TurboEngine(Settings())
            engine.prepare_runtime()
            engine.load()
            result['settings'] = plan['chatterbox_parameters']
        else:
            from qwen_tts import Qwen3TTSModel
            assets = json.loads((ROOT / 'model-cache/qwen3-benchmark/assets.json').read_text())
            asset = assets['assets'][0]
            assert asset['downloaded']
            engine = Qwen3TTSModel.from_pretrained(asset['snapshot'], device_map='cuda:0',
                        dtype=torch.bfloat16, attn_implementation='sdpa', local_files_only=True)
            result['settings'] = engine._merge_generate_kwargs(max_new_tokens=plan['qwen_max_new_tokens'])
            result['settings']['non_streaming_mode'] = args.config == 'qwen06_fulltext'
            result['dtype'] = str(next(engine.model.parameters()).dtype)
            result['attention_requested'] = 'sdpa'
        torch.cuda.synchronize()
        result['load_seconds'] = time.perf_counter() - started
        result['load_peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        if args.config != 'chatterbox_C':
            started = time.perf_counter()
            prompt = engine.create_voice_clone_prompt(ref_audio=str(reference),
                        ref_text=plan['reference_text'], x_vector_only_mode=False)
            torch.cuda.synchronize()
            result['reference_conditioning_seconds'] = time.perf_counter() - started
            result['reference_peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
            result['reference_peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
            original_generate = engine.model.generate
            code_lengths = []
            def recorded_generate(*a, **kw):
                answer = original_generate(*a, **kw)
                code_lengths[:] = [int(c.shape[0]) for c in answer[0]]
                return answer
            engine.model.generate = recorded_generate
        for passage in plan['passages']:
            if args.restart and passage['id'] != plan['restart_passage']:
                continue
            print('GENERATING', args.config, passage['id'], flush=True)
            random.seed(plan['seed'])
            np.random.seed(plan['seed'])
            torch.manual_seed(plan['seed'])
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            if args.config == 'chatterbox_C':
                audio = engine.synthesize(passage['text'], reference, plan['chatterbox_parameters'])
                wav, sr = audio.samples, audio.sample_rate
            else:
                with torch.inference_mode():
                    wavs, sr = engine.generate_voice_clone(text=passage['text'], language='English',
                        voice_clone_prompt=prompt, non_streaming_mode=args.config == 'qwen06_fulltext',
                        max_new_tokens=plan['qwen_max_new_tokens'])
                wav = np.asarray(wavs[0], dtype=np.float32).squeeze()
            torch.cuda.synchronize()
            assert wav.ndim == 1 and np.isfinite(wav).all() and np.max(np.abs(wav)) > 0
            record = {'passage': passage['id'], 'text': passage['text'], 'seed': plan['seed'],
                'seconds': time.perf_counter() - started, 'sample_rate': sr,
                'duration_seconds': len(wav) / sr, 'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
                'peak_reserved_bytes': torch.cuda.max_memory_reserved()}
            if args.config != 'chatterbox_C':
                record['codec_frames'] = list(code_lengths)
                record['hit_token_cap'] = any(n >= plan['qwen_max_new_tokens'] for n in code_lengths)
            path = out / (passage['id'] + '.wav')
            sf.write(path, wav, sr, subtype='FLOAT')
            record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            result['takes'].append(record)
            save()
            print(json.dumps(record), flush=True)
        result['status'] = 'completed'
    except Exception as exc:
        result['status'] = 'failed'
        result['error'] = repr(exc)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
