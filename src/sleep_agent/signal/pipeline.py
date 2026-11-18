from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import numpy as np

from sleep_agent.schemas import SessionMetadata, WindowMetrics
from sleep_agent.signal.metrics import compute_rr_metrics
from sleep_agent.signal.peaks import detect_r_peaks
from sleep_agent.signal.preprocessing import bandpass_valid_segments
from sleep_agent.signal.quality import assess_quality


def process_session(session: SessionMetadata, config: dict) -> list[WindowMetrics]:
    if not session.signal_path:
        raise ValueError("waveform session requires signal_path")
    bundle = np.load(Path(session.signal_path))
    raw = bundle["ecg_mv"]
    fs = float(bundle["fs_hz"])
    contact = bundle["contact"].astype(bool)
    motion = bundle["motion"].astype(bool)
    valid = np.isfinite(raw)
    sig = config["signal"]
    met = config["metrics"]
    qual = config["quality"]
    filtered = bandpass_valid_segments(raw, fs, sig["filter_low_hz"], sig["filter_high_hz"], sig["filter_order"])
    detection = detect_r_peaks(filtered, fs, sig["peak_min_distance_seconds"], sig["peak_prominence"])
    window_samples = int(met["window_seconds"] * fs)
    step_samples = int(met["step_seconds"] * fs)
    windows: list[WindowMetrics] = []
    for sequence, begin in enumerate(range(0, len(raw) - window_samples + 1, step_samples)):
        end = begin + window_samples
        peak_indices = detection.indices[(detection.indices >= begin) & (detection.indices < end)]
        peak_times = peak_indices / fs
        interval_valid = []
        for left, right in zip(peak_indices[:-1], peak_indices[1:]):
            interval_valid.append(bool(np.all(valid[left:right + 1] & contact[left:right + 1] & ~motion[left:right + 1])))
        prelim = compute_rr_metrics(
            peak_times, np.asarray(interval_valid, dtype=bool), met["rr_min_ms"],
            met["rr_max_ms"], min_valid_rr=2,
        )
        coverage = float(np.mean(valid[begin:end]))
        contact_fraction = float(np.mean(contact[begin:end]))
        motion_fraction = float(np.mean(motion[begin:end]))
        abnormal_fraction = 1 - prelim.valid_rr_count / max(len(prelim.rr_ms), 1)
        quality = assess_quality(
            coverage=coverage, contact_fraction=contact_fraction, motion_fraction=motion_fraction,
            abnormal_rr_fraction=abnormal_fraction, **qual,
        )
        enough = prelim.valid_rr_count >= met["min_valid_rr"] and prelim.adjacent_pair_count >= met["min_valid_rr"] - 1
        reasons = list(quality.reasons)
        if not enough:
            reasons.append("insufficient_valid_rr")
        usable = quality.usable and enough
        start = session.start_time + timedelta(seconds=begin / fs)
        windows.append(WindowMetrics(
            window_id=f"{session.session_id}-w{sequence:03d}", session_id=session.session_id,
            user_id=session.user_id, start_time=start,
            end_time=start + timedelta(seconds=met["window_seconds"]),
            heart_rate_bpm=round(prelim.heart_rate_bpm, 2) if usable and prelim.heart_rate_bpm else None,
            rmssd_ms=round(prelim.rmssd_ms, 2) if usable and prelim.rmssd_ms is not None else None,
            coverage=round(coverage, 4), contact_fraction=round(contact_fraction, 4),
            motion_fraction=round(motion_fraction, 4),
            quality_status="usable" if usable else "insufficient_quality", quality_reasons=reasons,
            valid_rr_count=prelim.valid_rr_count, window_seconds=met["window_seconds"],
            sampling_rate_hz=fs, algorithm_version=session.algorithm_version,
            source_kind="waveform_derived",
        ))
    output_path = Path(session.signal_path)
    np.savez_compressed(
        output_path, **{key: bundle[key] for key in bundle.files}, filtered_ecg_mv=filtered,
        detected_r_peaks_s=detection.indices / fs,
    )
    return windows
