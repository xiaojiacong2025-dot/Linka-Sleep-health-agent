from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import median

from sleep_agent.schemas import BaselineComparison, SessionMetadata, WindowMetrics
from sleep_agent.storage.database import connect


class Repository:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def upsert_session(self, session: SessionMetadata) -> None:
        with connect(self.database_path) as db:
            db.execute(
                """INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET user_id=excluded.user_id,
                start_time=excluded.start_time, end_time=excluded.end_time,
                sampling_rate_hz=excluded.sampling_rate_hz, signal_path=excluded.signal_path,
                source_kind=excluded.source_kind, algorithm_version=excluded.algorithm_version""",
                (session.session_id, session.user_id, session.start_time.isoformat(),
                 session.end_time.isoformat(), session.sampling_rate_hz, session.signal_path,
                 session.source_kind, session.algorithm_version),
            )

    def upsert_windows(self, windows: list[WindowMetrics]) -> None:
        rows = [(
            w.window_id, w.session_id, w.user_id, w.start_time.isoformat(), w.end_time.isoformat(),
            w.heart_rate_bpm, w.rmssd_ms, w.coverage, w.contact_fraction, w.motion_fraction,
            w.quality_status, json.dumps(w.quality_reasons), w.valid_rr_count, w.window_seconds,
            w.sampling_rate_hz, w.algorithm_version, w.source_kind,
        ) for w in windows]
        with connect(self.database_path) as db:
            db.executemany(
                """INSERT INTO window_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(window_id) DO UPDATE SET
                heart_rate_bpm=excluded.heart_rate_bpm, rmssd_ms=excluded.rmssd_ms,
                coverage=excluded.coverage, contact_fraction=excluded.contact_fraction,
                motion_fraction=excluded.motion_fraction, quality_status=excluded.quality_status,
                quality_reasons=excluded.quality_reasons, valid_rr_count=excluded.valid_rr_count""", rows,
            )

    def list_sessions(self, user_id: str) -> list[dict]:
        with connect(self.database_path) as db:
            rows = db.execute(
                "SELECT * FROM sessions WHERE user_id=? ORDER BY start_time", (user_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, user_id: str, session_id: str) -> dict | None:
        with connect(self.database_path) as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE user_id=? AND session_id=?", (user_id, session_id)
            ).fetchone()
        return dict(row) if row else None

    def query_metrics(
        self, user_id: str, start_time: datetime, end_time: datetime,
        metric: str, limit: int = 500,
    ) -> list[dict]:
        column = {"heart_rate": "heart_rate_bpm", "rmssd": "rmssd_ms"}.get(metric)
        if column is None:
            raise ValueError("unsupported metric")
        limit = min(max(limit, 1), 2000)
        with connect(self.database_path) as db:
            rows = db.execute(
                f"""SELECT window_id, session_id, start_time, end_time, {column} AS value,
                quality_status, quality_reasons, coverage, window_seconds, algorithm_version,
                source_kind FROM window_metrics WHERE user_id=? AND start_time>=? AND end_time<=?
                ORDER BY start_time LIMIT ?""",
                (user_id, start_time.isoformat(), end_time.isoformat(), limit),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["quality_reasons"] = json.loads(item["quality_reasons"])
            result.append(item)
        return result

    def compare_periods(
        self, user_id: str, metric: str,
        target_start: datetime, target_end: datetime,
        baseline_start: datetime, baseline_end: datetime,
    ) -> BaselineComparison:
        target = self.query_metrics(user_id, target_start, target_end, metric, 2000)
        baseline = self.query_metrics(user_id, baseline_start, baseline_end, metric, 2000)
        target_valid = [row for row in target if row["value"] is not None and row["quality_status"] == "usable"]
        base_valid = [row for row in baseline if row["value"] is not None and row["quality_status"] == "usable"]
        unit = "bpm" if metric == "heart_rate" else "ms"
        if not target_valid:
            return BaselineComparison(status="no_target_data", metric=metric, unit=unit,
                                      limitations=["目标时段没有可用数据"])
        if len(base_valid) < 3:
            return BaselineComparison(status="insufficient_baseline", metric=metric, unit=unit,
                                      limitations=["历史基线至少需要三个可用窗口"])
        signatures = {(r["window_seconds"], r["algorithm_version"], r["source_kind"])
                      for r in target_valid + base_valid}
        if len(signatures) != 1:
            return BaselineComparison(status="incomparable", metric=metric, unit=unit,
                                      limitations=["窗口长度、算法版本或数据来源类型不一致"])
        target_value = float(median(r["value"] for r in target_valid))
        baseline_value = float(median(r["value"] for r in base_valid))
        if baseline_value == 0:
            return BaselineComparison(status="incomparable", metric=metric, unit=unit,
                                      limitations=["基线为零，无法计算百分比变化"])
        return BaselineComparison(
            status="ok", metric=metric, unit=unit, target_value=round(target_value, 2),
            baseline_value=round(baseline_value, 2),
            change_pct=round((target_value - baseline_value) / baseline_value * 100, 2),
            target_evidence_ids=[r["window_id"] for r in target_valid],
            baseline_evidence_ids=[r["window_id"] for r in base_valid],
            limitations=["比较值是可用窗口中位数，不等同于整晚重新计算的指标"],
        )

