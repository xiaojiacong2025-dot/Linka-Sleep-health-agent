# Data dictionary

All database timestamps are timezone-aware ISO 8601 strings representing UTC instants. The UI may display them in `APP_TIMEZONE`.

| Field | Type | Unit / meaning |
|---|---|---|
| `heart_rate_bpm` | nullable float | beats per minute; null means unavailable |
| `rmssd_ms` | nullable float | milliseconds; null means unavailable |
| `coverage` | float | fraction of finite samples in a window |
| `contact_fraction` | float | fraction marked as acceptable contact |
| `motion_fraction` | float | fraction marked as motion |
| `quality_status` | string | `usable` or `insufficient_quality` |
| `quality_reasons` | JSON list | stable, machine-readable rejection reasons |
| `window_seconds` | integer | metric window duration |
| `algorithm_version` | string | calculation or simulation version |
| `source_kind` | string | `waveform_derived` or `direct_simulation` |

Nightly comparison uses the median of usable, stored windows. It is not described as a whole-night RMSSD recomputed from all NN intervals. Overlapping waveform windows are retained for trend display; they are not treated as independent observations in statistical claims.

