from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt


def contiguous_true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    edges = np.diff(np.r_[False, mask.astype(bool), False].astype(int))
    return list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0]))


def bandpass_valid_segments(
    signal: np.ndarray, fs_hz: float, low_hz: float = 0.5,
    high_hz: float = 35.0, order: int = 4,
) -> np.ndarray:
    if not 0 < low_hz < high_hz < fs_hz / 2:
        raise ValueError("filter cutoffs must satisfy 0 < low < high < Nyquist")
    result = np.full(signal.shape, np.nan, dtype=float)
    sos = butter(order, [low_hz, high_hz], btype="bandpass", fs=fs_hz, output="sos")
    for start, end in contiguous_true_runs(np.isfinite(signal)):
        if end - start < max(round(3 * fs_hz), 64):
            continue
        try:
            result[start:end] = sosfiltfilt(sos, signal[start:end])
        except ValueError:
            continue
    return result

