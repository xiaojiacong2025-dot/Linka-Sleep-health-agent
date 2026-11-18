from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class MetricResult:
    heart_rate_bpm: float | None
    rmssd_ms: float | None
    valid_rr_count: int
    adjacent_pair_count: int
    rr_ms: np.ndarray
    rr_valid: np.ndarray


def compute_rr_metrics(
    peak_times_s: np.ndarray, interval_valid: np.ndarray | None = None,
    rr_min_ms: float = 400, rr_max_ms: float = 1500, min_valid_rr: int = 2,
) -> MetricResult:
    rr = np.diff(np.asarray(peak_times_s, dtype=float)) * 1000
    valid = np.isfinite(rr) & (rr >= rr_min_ms) & (rr <= rr_max_ms)
    if interval_valid is not None:
        interval_valid = np.asarray(interval_valid, dtype=bool)
        if interval_valid.shape != rr.shape:
            raise ValueError("interval_valid must have one item per RR interval")
        valid &= interval_valid
    pairs = valid[:-1] & valid[1:] if len(valid) > 1 else np.array([], dtype=bool)
    if int(valid.sum()) < min_valid_rr:
        return MetricResult(None, None, int(valid.sum()), int(pairs.sum()), rr, valid)
    hr = float(60000 / np.median(rr[valid]))
    rmssd = float(np.sqrt(np.mean(np.diff(rr)[pairs] ** 2))) if pairs.any() else None
    return MetricResult(hr, rmssd, int(valid.sum()), int(pairs.sum()), rr, valid)

