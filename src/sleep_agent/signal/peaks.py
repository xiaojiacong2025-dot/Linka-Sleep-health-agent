from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.signal import find_peaks


@dataclass(frozen=True)
class PeakDetection:
    indices: np.ndarray
    prominence: np.ndarray
    method: str = "scipy_find_peaks_demo"


def detect_r_peaks(
    filtered: np.ndarray, fs_hz: float, min_distance_seconds: float = 0.3,
    prominence: float = 0.45,
) -> PeakDetection:
    safe = np.nan_to_num(filtered, nan=0.0)
    indices, props = find_peaks(
        safe, distance=max(1, int(min_distance_seconds * fs_hz)), prominence=prominence
    )
    return PeakDetection(indices=indices, prominence=props.get("prominences", np.array([])))

