import numpy as np
import pytest

from sleep_agent.signal.metrics import compute_rr_metrics


def test_known_rr_metrics():
    peaks = np.cumsum([0, 1.0, 1.02, 0.98, 1.01])
    result = compute_rr_metrics(peaks, min_valid_rr=2)
    expected = np.sqrt(np.mean(np.diff([1000, 1020, 980, 1010]) ** 2))
    assert result.heart_rate_bpm == pytest.approx(60000 / 1005)
    assert result.rmssd_ms == pytest.approx(expected)


def test_invalid_interval_does_not_bridge_neighbors():
    peaks = np.cumsum([0, 1.0, 1.1, 1.0, 0.9])
    result = compute_rr_metrics(peaks, np.array([True, False, True, True]), min_valid_rr=2)
    assert result.adjacent_pair_count == 1
    assert result.rmssd_ms == pytest.approx(100)

