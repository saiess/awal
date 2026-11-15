import json
import math
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from uuid import uuid4

import numpy as np
import soundfile as sf

from .config import SAMPLE_RATE
from .projects import file_hash, now


def validate_audio(samples, sample_rate):
    a = np.asarray(samples, dtype=np.float32)
    if sample_rate != SAMPLE_RATE or a.ndim != 1 or not len(a):
        raise ValueError("Engine output must be nonempty mono audio at 24 kHz.")
    if not np.isfinite(a).all() or np.max(np.abs(a)) > 8:
        raise ValueError("Engine produced invalid audio values.")
    if np.max(np.abs(a)) < 1e-5 or np.ptp(a) < 1e-5:
        raise ValueError("Engine produced silent or flat audio.")
    return a


def write_raw(path, samples, sr):
    a = validate_audio(samples, sr)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.stem + ".tmp.wav")
    try:
        sf.write(temp, a, sr, subtype="FLOAT")
        check, rate = sf.read(temp, dtype="float32")
        validate_audio(check, rate)
        if not np.array_equal(a, check):
            raise ValueError("Raw audio failed its save verification.")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return {"duration_seconds": len(a)/sr, "sample_rate": sr, "sha256": file_hash(path)}


def ffmpeg():
    explicit = os.environ.get("TTS_FFMPEG")
    if explicit:
        if not Path(explicit).is_file():
            raise RuntimeError("TTS_FFMPEG does not point to an executable.")
        return explicit
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def convert(source, target, speed=1.0, codec="pcm_f32le"):
    command = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
               "-map", "0:a:0", "-vn"]
    if speed != 1.0:
        command += ["-af", f"atempo={speed:.8g}"]
    command += ["-c:a", codec]
    if codec == "libmp3lame":
        command += ["-q:a", "2"]
    command += [str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError("FFmpeg could not process the audio. Check the local application log.")


def combine(arrays, gap_seconds):
    gap = round(gap_seconds * SAMPLE_RATE)
    parts, inserted = [], 0
    threshold = 10 ** (-45 / 20)
    def quiet_length(a):
        index = np.flatnonzero(np.abs(a[:gap]) >= threshold)
        return int(index[0]) if len(index) else min(gap, len(a))
    for i, array in enumerate(arrays):
        if i and gap:
            extra = max(0, gap - quiet_length(arrays[i-1][::-1]) - quiet_length(array))
            if extra:
                parts.append(np.zeros(extra, dtype=np.float32))
                inserted += extra
        parts.append(array)
    return np.concatenate(parts), inserted / SAMPLE_RATE


def smooth_joins(arrays):
    """Conservative export-only edge cleanup; never remove interior pauses."""
    result = [a.copy() for a in arrays]
    threshold = 10 ** (-55 / 20)
    minimum = round(.5 * SAMPLE_RATE)
    retained = round(.15 * SAMPLE_RATE)
    fade = round(.003 * SAMPLE_RATE)
    removed = 0

    def quiet_edge(a):
        # Use peaks in 10 ms frames, so a single audible sample protects its frame.
        frame = round(.01 * SAMPLE_RATE)
        count = len(a) // frame
        peaks = np.max(np.abs(a[:count * frame].reshape(count, frame)), axis=1) if count else []
        audible = np.flatnonzero(np.asarray(peaks) >= threshold)
        # If the whole section is unusually quiet, do not guess where speech starts.
        return int(audible[0]) * frame if len(audible) else 0

    for i in range(len(result) - 1):
        left, right = result[i], result[i + 1]
        tail, head = quiet_edge(left[::-1]), quiet_edge(right)
        trim_tail = tail - retained if tail >= minimum else 0
        trim_head = head - retained if head >= minimum else 0
        left = left[:len(left) - trim_tail]
        right = right[trim_head:]
        removed += trim_tail + trim_head
        # Short fades soften a discontinuous join without overlapping words.
        n = min(fade, len(left) // 2)
        if n:
            left[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
        n = min(fade, len(right) // 2)
        if n:
            right[:n] *= np.linspace(0, 1, n, dtype=np.float32)
        result[i], result[i + 1] = left, right
    return result, {"trimmed_seconds": removed / SAMPLE_RATE, "quiet_threshold_dbfs": -55,
                    "minimum_quiet_seconds": .5, "retained_edge_seconds": .15, "fade_seconds": .003}


def protect_peak(path, ceiling_dbfs=-1):
    """Attenuation only, applied to an export working copy; no hard clipping."""
    a, sr = sf.read(path, dtype="float32")
    validate_audio(a, sr)
    peak = float(np.max(np.abs(a)))
    gain_db = min(0.0, ceiling_dbfs - 20 * math.log10(peak))
    if gain_db < 0:
        a *= 10 ** (gain_db / 20)
        sf.write(path, a, sr, subtype="FLOAT")
    return {"gain_db": gain_db, "sample_peak_ceiling_dbfs": ceiling_dbfs}


def finish_master(source, target, format, processed):
    protection = protect_peak(source) if processed else None
    ceiling = 10 ** (-1 / 20)
    # MP3 encoding can introduce new peaks. Check the decoded result and, if
    # necessary, attenuate the working WAV and encode again before delivering it.
    for attempt in range(3):
        if format == "wav":
            shutil.copyfile(source, target)
        else:
            convert(source, target, codec="libmp3lame")
        decoded, sr = sf.read(target, dtype="float32")
        validate_audio(decoded, sr)
        peak = float(np.max(np.abs(decoded)))
        if not processed or peak <= ceiling + 1e-6:
            if protection is not None:
                protection["decoded_sample_peak_dbfs"] = 20 * math.log10(peak)
            return decoded, sr, protection
        original, _ = sf.read(source, dtype="float32")
        current_dbfs = 20 * math.log10(float(np.max(np.abs(original))))
        adjustment = protect_peak(source, current_dbfs - 20 * math.log10(peak / ceiling) - .1)
        protection["gain_db"] += adjustment["gain_db"]
    raise RuntimeError("Export peaks could not be kept within the safety ceiling.")


def enhance(path):
    """Optional static gain only: bounded loudness adjustment with peak headroom."""
    import pyloudnorm as pyln
    a, sr = sf.read(path, dtype="float32")
    loudness = float(pyln.Meter(sr).integrated_loudness(a)) if len(a) >= .4*sr else None
    gain_db = max(-12, min(6, -18-loudness)) if loudness is not None and math.isfinite(loudness) else 0
    peak_limit = 10 ** (-1/20)
    gain_db = min(gain_db, 20*math.log10(peak_limit / float(np.max(np.abs(a)))))
    a *= 10 ** (gain_db/20)
    sf.write(path, a, sr, subtype="FLOAT")
    return {"method": "static gain; no compressor", "requested_lufs": -18,
            "input_lufs": loudness if loudness is not None and math.isfinite(loudness) else None,
            "gain_db": gain_db, "sample_peak_ceiling_dbfs": -1}


def export_project(store, project_id, options):
    p = store.read(project_id)
    ids = [str(i) for i in options.segment_ids] if options.segment_ids else [s["id"] for s in p["segments"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Select each section once.")
    selected = [store.segment(p, i) for i in ids]
    selected.sort(key=lambda s: s["order"])
    if any(s["status"] != "ready" or s["stale"] or not s["audio_path"] for s in selected):
        raise ValueError("Generate all selected sections before exporting; some are missing, failed, or stale.")
    if options.enhance and not options.processed:
        raise ValueError("Enable processed export to apply volume enhancement.")
    export_id = str(uuid4())
    folder = store.project_dir(project_id) / "exports" / export_id
    folder.mkdir(parents=True)
    effective_speed = options.speed if options.processed else 1.0
    raw_hashes, arrays = {}, []
    for s in selected:
        path = store.project_file(project_id, s["audio_path"])
        a, sr = sf.read(path, dtype="float32")
        arrays.append(validate_audio(a, sr))
        raw_hashes[s["id"]] = file_hash(path)
    join_processing = None
    if options.processed:
        arrays, join_processing = smooth_joins(arrays)
    assembled, inserted = combine(arrays, options.gap_seconds)
    working = folder / "assembly.wav"
    sf.write(working, assembled, SAMPLE_RATE, subtype="FLOAT")
    tempo = folder / "processed.wav"
    if effective_speed != 1:
        convert(working, tempo, effective_speed)
    else:
        shutil.copyfile(working, tempo)
    enhancement = enhance(tempo) if options.enhance else None
    master = folder / ("master." + options.format)
    decoded, sr, peak_protection = finish_master(tempo, master, options.format, options.processed)
    expected = len(assembled)/SAMPLE_RATE/effective_speed
    if abs(len(decoded)/sr - expected) > .15:
        raise RuntimeError("Export duration differs unexpectedly from its input sections.")
    record = {"id": export_id, "created_at": now(), "options": options.model_dump(mode="json"),
              "effective_speed": effective_speed, "segment_ids": [s["id"] for s in selected],
              "raw_sha256": raw_hashes, "inserted_gap_seconds": inserted,
              "duration_seconds": len(decoded)/sr, "enhancement": enhancement,
              "join_processing": join_processing, "peak_protection": peak_protection,
              "audio_path": master.relative_to(store.root).as_posix()}
    artifact = master
    if options.include_segments:
        artifact = folder / "segments.zip"
        with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_STORED) as z:
            z.write(master, master.name)
            for i, s in enumerate(selected):
                raw = store.project_file(project_id, s["audio_path"])
                individual = folder / f"section-{i+1:03}.wav"
                if effective_speed != 1:
                    convert(raw, individual, effective_speed)
                else:
                    shutil.copyfile(raw, individual)
                if options.enhance:
                    enhance(individual)
                if options.processed:
                    protect_peak(individual)
                z.write(individual, individual.name)
                individual.unlink()
            z.writestr("sections.json", json.dumps({"export": record, "sections": selected}, indent=2))
    record["download_path"] = artifact.relative_to(store.root).as_posix()
    record["sha256"] = file_hash(artifact)
    # Raw audio is immutable, including when export/FFmpeg fails.
    for s in selected:
        if file_hash(store.project_file(project_id, s["audio_path"])) != raw_hashes[s["id"]]:
            raise RuntimeError("A raw section changed during export.")
    working.unlink()
    tempo.unlink()
    def commit(project):
        project["export_settings"] = options.model_dump(include={"speed", "processed", "enhance", "gap_seconds"})
        project["exports"].append(record)
    store.change(project_id, commit)
    return record
