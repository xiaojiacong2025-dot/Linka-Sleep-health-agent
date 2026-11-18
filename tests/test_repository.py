from datetime import UTC, datetime, timedelta

from sleep_agent.data.simulate import simulate_multinight_metrics
from sleep_agent.storage.database import initialize_database
from sleep_agent.storage.repository import Repository


def test_repository_isolates_users_and_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    initialize_database(db)
    repo = Repository(db)
    sessions, windows = simulate_multinight_metrics(
        start_date=datetime(2026, 1, 1, tzinfo=UTC), nights=2
    )
    for session in sessions:
        repo.upsert_session(session)
    repo.upsert_windows(windows)
    repo.upsert_windows(windows)
    rows = repo.query_metrics("demo_user", sessions[0].start_time,
                              sessions[-1].end_time, "rmssd", 2000)
    assert len(rows) == len(windows)
    assert repo.query_metrics("other_user", sessions[0].start_time,
                              sessions[-1].end_time, "rmssd") == []

