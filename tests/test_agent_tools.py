from datetime import UTC, datetime

from sleep_agent.agent.tools import AgentTools
from sleep_agent.settings import load_settings
from sleep_agent.storage.database import initialize_database
from sleep_agent.storage.repository import Repository


def test_tools_reject_unsupported_metric(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    settings = load_settings()
    initialize_database(settings.database_path)
    tools = AgentTools(settings, Repository(settings.database_path), "demo_user")
    result = tools.call("get_metrics", {"metric": "spo2",
                        "start_time": datetime(2026, 1, 1, tzinfo=UTC),
                        "end_time": datetime(2026, 1, 2, tzinfo=UTC)})
    assert result.status == "error"

