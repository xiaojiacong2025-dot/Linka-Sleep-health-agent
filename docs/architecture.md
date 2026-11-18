# Architecture

The project has two deterministic data paths and one conversational path.

```text
synthetic waveform -> offline filtering -> R peaks -> quality gates -> HR/RMSSD -> SQLite
direct multi-night simulation -----------------------------------------------> SQLite
public knowledge notes -> stable chunks -> Chinese bigram FTS5 index --------> SQLite
user question -> scoped tools -> data/knowledge evidence -> Agent response
```

The `waveform_derived` source is calculated from the synthetic ECG. The `direct_simulation` source exists only to provide multiple nights for baseline demonstrations. The repository rejects baseline comparisons when source type, algorithm version, or window length differs.

Filtering is offline and uses zero-phase processing on each continuous valid segment. A real BLE service would require packet sequence validation, clock alignment, buffered causal filters, backpressure, and device-specific validation.

The API fixes the demo identity on the server. This is a local demonstration and does not implement production authentication or multi-tenant authorization.

