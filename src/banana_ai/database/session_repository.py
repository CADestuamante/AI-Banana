"""
SessionRepository — CRUD cho bảng scan_sessions.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from banana_ai.database.connection import get_connection
from banana_ai.database.models import ScanSession


class SessionRepository:
    """Thao tác CRUD với bảng scan_sessions."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    # --- Tạo phiên quét ---

    def create(
        self,
        operator_id: int,
        source_type: str,
        source_detail: str,
        batch_code: Optional[str] = None,
    ) -> ScanSession:
        if source_type not in ("camera", "file"):
            raise ValueError(f"source_type không hợp lệ: '{source_type}'.")
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
        if batch_code is None:
            batch_code = self._generate_batch_code(now)
        sql = """
            INSERT INTO scan_sessions (batch_code, operator_id, source_type, source_detail, started_at)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            with get_connection(self._db_path) as conn:
                cursor = conn.execute(sql, (batch_code, operator_id, source_type, source_detail, now_str))
                conn.commit()
                return ScanSession(
                    id=cursor.lastrowid,
                    batch_code=batch_code,
                    operator_id=operator_id,
                    source_type=source_type,
                    source_detail=source_detail,
                    started_at=now,
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Mã mẻ hàng '{batch_code}' đã tồn tại.") from exc

    def _generate_batch_code(self, dt: datetime) -> str:
        """Sinh mã mẻ hàng tự động: ME_YYYYMMDD_NN."""
        date_str = dt.strftime("%Y%m%d")
        prefix = f"ME_{date_str}_"
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM scan_sessions WHERE batch_code LIKE ?",
                (prefix + "%",),
            ).fetchone()
        count = (row["cnt"] if row else 0) + 1
        return f"{prefix}{count:02d}"

    # --- Kết thúc phiên ---

    def close_session(self, session_id: int) -> None:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        with get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE scan_sessions SET ended_at = ? WHERE id = ?",
                (now_str, session_id),
            )
            conn.commit()

    # --- Truy vấn ---

    def get_by_id(self, session_id: int) -> Optional[ScanSession]:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return _row_to_session(row) if row else None

    def get_by_batch_code(self, batch_code: str) -> Optional[ScanSession]:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions WHERE batch_code = ?", (batch_code,)
            ).fetchone()
        return _row_to_session(row) if row else None

    def list_all(self, limit: int = 100) -> List[ScanSession]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM scan_sessions ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_session(r) for r in rows]

    def list_by_operator(self, operator_id: int) -> List[ScanSession]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM scan_sessions WHERE operator_id = ? ORDER BY started_at DESC",
                (operator_id,),
            ).fetchall()
        return [_row_to_session(r) for r in rows]

    def list_by_date(self, date_str: str) -> List[ScanSession]:
        """date_str định dạng 'YYYY-MM-DD'."""
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM scan_sessions WHERE DATE(started_at) = ? ORDER BY started_at",
                (date_str,),
            ).fetchall()
        return [_row_to_session(r) for r in rows]

    def list_by_month(self, year: int, month: int) -> List[ScanSession]:
        month_prefix = f"{year:04d}-{month:02d}"
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM scan_sessions WHERE strftime('%Y-%m', started_at) = ? ORDER BY started_at",
                (month_prefix,),
            ).fetchall()
        return [_row_to_session(r) for r in rows]

    # --- Xóa ---

    def delete(self, session_id: int) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute("DELETE FROM scan_sessions WHERE id = ?", (session_id,))
            conn.commit()


def _row_to_session(row: sqlite3.Row) -> ScanSession:
    return ScanSession(
        id=row["id"],
        batch_code=row["batch_code"],
        operator_id=row["operator_id"],
        source_type=row["source_type"],
        source_detail=row["source_detail"],
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
    )