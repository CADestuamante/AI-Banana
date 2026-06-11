"""
Quản lý kết nối SQLite và khởi tạo schema.
"""

import sqlite3
from pathlib import Path


_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    full_name       TEXT    NOT NULL,
    employee_id     TEXT    NOT NULL UNIQUE,
    role            TEXT    NOT NULL CHECK (role IN ('admin', 'operator', 'manager')),
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'blocked')),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_code      TEXT    NOT NULL UNIQUE,
    operator_id     INTEGER NOT NULL REFERENCES users(id),
    source_type     TEXT    NOT NULL CHECK (source_type IN ('camera', 'file')),
    source_detail   TEXT    NOT NULL,
    started_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    ended_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_operator ON scan_sessions(operator_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started  ON scan_sessions(started_at);

CREATE TABLE IF NOT EXISTS scan_analytics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES scan_sessions(id) ON DELETE CASCADE,
    banana_green    INTEGER NOT NULL DEFAULT 0,
    banana_turning  INTEGER NOT NULL DEFAULT 0,
    banana_ripe     INTEGER NOT NULL DEFAULT 0,
    banana_overripe INTEGER NOT NULL DEFAULT 0,
    total_count     INTEGER NOT NULL DEFAULT 0,
    quality_rate    REAL    NOT NULL DEFAULT 0.0,
    recorded_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_analytics_session  ON scan_analytics(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_recorded ON scan_analytics(recorded_at);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Mở kết nối SQLite với row_factory để truy cập cột bằng tên."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_database(db_path: str) -> None:
    """Tạo file database và toàn bộ bảng nếu chưa tồn tại."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(_SCHEMA_SQL)
    print(f"[DB] Database sẵn sàng tại: {db_path}")