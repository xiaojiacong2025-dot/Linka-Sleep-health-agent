from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class IngestionReport:
    sample_count: int
    duplicate_count: int
    out_of_order_count: int
    missing_count: int


def validate_sample_indices(indices: np.ndarray, values: np.ndarray) -> IngestionReport:
    if indices.ndim != 1 or values.ndim != 1 or len(indices) != len(values):
        raise ValueError("indices and values must be one-dimensional and equally sized")
    diffs = np.diff(indices)
    duplicates = int(np.count_nonzero(diffs == 0))
    out_of_order = int(np.count_nonzero(diffs < 0))
    positive = diffs[diffs > 0]
    missing = int(np.sum(np.maximum(positive - 1, 0)))
    return IngestionReport(len(indices), duplicates, out_of_order, missing)

