from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sleep_agent.data.simulate import simulate_multinight_metrics, simulate_waveform
from sleep_agent.settings import load_settings
from sleep_agent.signal.pipeline import process_session
from sleep_agent.storage.database import initialize_database
from sleep_agent.storage.repository import Repository


def main() -> None:
    settings = load_settings()
    initialize_database(settings.database_path)
    repository = Repository(settings.database_path)
    sim = settings.config["simulation"]
    raw_path = settings.project_root / "data" / "raw" / "waveform-demo-001.npz"
    session, _ = simulate_waveform(
        raw_path, seed=sim["seed"], sampling_rate_hz=sim["sampling_rate_hz"],
        duration_seconds=sim["duration_seconds"],
    )
    windows = process_session(session, settings.config)
    repository.upsert_session(session)
    repository.upsert_windows(windows)
    start = datetime(2026, 11, 7, 14, 30, tzinfo=UTC)
    night_sessions, night_windows = simulate_multinight_metrics(
        start_date=start, nights=sim["demo_nights"], seed=sim["seed"]
    )
    for item in night_sessions:
        repository.upsert_session(item)
    repository.upsert_windows(night_windows)
    print({
        "database": str(settings.database_path), "sessions": 1 + len(night_sessions),
        "waveform_windows": len(windows),
        "waveform_usable": sum(w.quality_status == "usable" for w in windows),
        "direct_simulation_windows": len(night_windows),
    })


if __name__ == "__main__":
    main()

