from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from sleep_agent.schemas import SessionMetadata, WindowMetrics


def simulate_waveform(
    output_path: Path,
    *,
    seed: int = 42,
    sampling_rate_hz: int = 250,
    duration_seconds: int = 900,
    start_time: datetime | None = None,
) -> tuple[SessionMetadata, np.ndarray]:
    """Create a reproducible ECG-like waveform with labelled demo faults."""
    rng = np.random.default_rng(seed)
    fs = sampling_rate_hz
    start = start_time or datetime(2026, 11, 17, 14, 0, tzinfo=UTC)
    t = np.arange(fs * duration_seconds, dtype=float) / fs
    beats: list[float] = []
    now = 1.0
    while now < duration_seconds - 1:
        beats.append(now)
        now += 1.0 + 0.035 * np.sin(2 * np.pi * 0.22 * now) + rng.normal(0, 0.008)
    truth_peaks = np.asarray(beats)
    clean = np.zeros_like(t)
    for beat in truth_peaks:
        center = round(beat * fs)
        lo, hi = max(0, center - 100), min(t.size, center + 140)
        dt = t[lo:hi] - beat
        clean[lo:hi] += (
            1.2 * np.exp(-0.5 * (dt / 0.012) ** 2)
            - 0.22 * np.exp(-0.5 * ((dt - 0.025) / 0.012) ** 2)
            + 0.12 * np.exp(-0.5 * ((dt + 0.18) / 0.035) ** 2)
            + 0.25 * np.exp(-0.5 * ((dt - 0.28) / 0.06) ** 2)
        )
    motion = (t >= 360) & (t < 410)
    contact = ~((t >= 640) & (t < 680))
    missing = (t >= 180) & (t < 183)
    raw = clean + 0.2 * np.sin(2 * np.pi * 0.18 * t) + rng.normal(0, 0.025, t.size)
    raw += motion * rng.normal(0, 0.6, t.size)
    raw[~contact] = rng.normal(0, 0.005, np.count_nonzero(~contact))
    raw[missing] = np.nan
    acceleration = 1 + rng.normal(0, 0.01, t.size) + motion * rng.normal(0, 0.15, t.size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        time_s=t,
        ecg_mv=raw,
        acc_magnitude_g=acceleration,
        motion=motion,
        contact=contact,
        missing=missing,
        truth_r_peaks_s=truth_peaks,
        fs_hz=fs,
    )
    session = SessionMetadata(
        session_id="waveform-demo-001",
        user_id="demo_user",
        start_time=start,
        end_time=start + timedelta(seconds=duration_seconds),
        sampling_rate_hz=fs,
        signal_path=str(output_path.resolve()),
        source_kind="waveform_derived",
    )
    return session, truth_peaks


def simulate_multinight_metrics(
    *, start_date: datetime, nights: int = 10, seed: int = 42
) -> tuple[list[SessionMetadata], list[WindowMetrics]]:
    """Create directly simulated nightly metrics for Agent history demos."""
    rng = np.random.default_rng(seed + 1)
    sessions: list[SessionMetadata] = []
    windows: list[WindowMetrics] = []
    for day in range(nights):
        start = (start_date + timedelta(days=day)).replace(hour=22, minute=30, second=0, microsecond=0)
        end = start + timedelta(hours=8)
        session_id = f"night-demo-{day + 1:03d}"
        sessions.append(SessionMetadata(
            session_id=session_id, user_id="demo_user", start_time=start, end_time=end,
            source_kind="direct_simulation", algorithm_version="demo-direct-0.1",
        ))
        night_hr = 59 + rng.normal(0, 2.2)
        night_rmssd = 39 + rng.normal(0, 4.0)
        for index in range(16):
            w_start = start + timedelta(minutes=30 * index)
            bad = day == 4 and index in {5, 6, 7}
            windows.append(WindowMetrics(
                window_id=f"{session_id}-w{index:02d}", session_id=session_id, user_id="demo_user",
                start_time=w_start, end_time=w_start + timedelta(minutes=5),
                heart_rate_bpm=None if bad else round(float(night_hr + rng.normal(0, 1.5)), 2),
                rmssd_ms=None if bad else round(float(max(12, night_rmssd + rng.normal(0, 3))), 2),
                coverage=0.72 if bad else 1.0, contact_fraction=0.75 if bad else 1.0,
                motion_fraction=0.22 if bad else round(float(rng.uniform(0, 0.025)), 4),
                quality_status="insufficient_quality" if bad else "usable",
                quality_reasons=["contact_below_threshold", "excessive_motion"] if bad else [],
                valid_rr_count=0 if bad else 295, window_seconds=300,
                algorithm_version="demo-direct-0.1", source_kind="direct_simulation",
            ))
    return sessions, windows

