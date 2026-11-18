from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  sampling_rate_hz REAL,
  signal_path TEXT,
  source_kind TEXT NOT NULL,
  algorithm_version TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_time ON sessions(user_id, start_time, end_time);
CREATE TABLE IF NOT EXISTS window_metrics (
  window_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  heart_rate_bpm REAL,
  rmssd_ms REAL,
  coverage REAL NOT NULL,
  contact_fraction REAL NOT NULL,
  motion_fraction REAL NOT NULL,
  quality_status TEXT NOT NULL,
  quality_reasons TEXT NOT NULL,
  valid_rr_count INTEGER NOT NULL,
  window_seconds INTEGER NOT NULL,
  sampling_rate_hz REAL,
  algorithm_version TEXT NOT NULL,
  source_kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metrics_user_time ON window_metrics(user_id, start_time, end_time);
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  chunk_id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  search_text TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_title TEXT NOT NULL,
  source_url TEXT NOT NULL,
  section TEXT NOT NULL,
  content_hash TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
  chunk_id UNINDEXED, search_text, tokenize='unicode61'
);
"""


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

