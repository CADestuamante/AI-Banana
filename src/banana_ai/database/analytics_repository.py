"""
AnalyticsRepository — CRUD cho bảng scan_analytics.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from banana_ai.database.connection import get_connection
from banana_ai.database.models import ScanAnalytics


class AnalyticsRepository:
    """Thao tác CRUD với bảng scan_analytics."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    # --- Ghi kết quả ---

    def save(
        self,
        session_id: int,
        banana_green: int,
        banana_turning: int,
        banana_ripe: int,
        banana_overripe: int,
    ) -> ScanAnalytics:
        """Lưu kết quả phân loại. Tự tính total_count và quality_rate."""
        analytics = ScanAnalytics(
            session_id=session_id,
            banana_green=banana_green,
            banana_turning=banana_turning,
            banana_ripe=banana_ripe,
            banana_overripe=banana_overripe,
        )
        analytics.recalculate()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        sql = """
            INSERT INTO scan_analytics
                (session_id, banana_green, banana_turning, banana_ripe,
                 banana_overripe, total_count, quality_rate, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with get_connection(self._db_path) as conn:
            cursor = conn.execute(sql, (
                analytics.session_id,
                analytics.banana_green,
                analytics.banana_turning,
                analytics.banana_ripe,
                analytics.banana_overripe,
                analytics.total_count,
                analytics.quality_rate,
                now_str,
            ))
            conn.commit()
            analytics.id = cursor.lastrowid
            analytics.recorded_at = datetime.fromisoformat(now_str)
        return analytics

    # --- Truy vấn ---

    def get_by_session(self, session_id: int) -> Optional[ScanAnalytics]:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scan_analytics WHERE session_id = ? ORDER BY recorded_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        return _row_to_analytics(row) if row else None

    def list_by_session(self, session_id: int) -> List[ScanAnalytics]:
        """Tất cả snapshots của một phiên (dùng cho biểu đồ real-time)."""
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM scan_analytics WHERE session_id = ? ORDER BY recorded_at",
                (session_id,),
            ).fetchall()
        return [_row_to_analytics(r) for r in rows]

    def summary_by_date(self, date_str: str) -> Dict:
        """Tổng hợp theo ngày. date_str: 'YYYY-MM-DD'."""
        sql = """
            SELECT
                SUM(a.banana_green)    AS total_green,
                SUM(a.banana_turning)  AS total_turning,
                SUM(a.banana_ripe)     AS total_ripe,
                SUM(a.banana_overripe) AS total_overripe,
                SUM(a.total_count)     AS grand_total,
                COUNT(DISTINCT a.session_id) AS session_count
            FROM scan_analytics a
            JOIN scan_sessions s ON a.session_id = s.id
            WHERE DATE(s.started_at) = ?
        """
        with get_connection(self._db_path) as conn:
            row = conn.execute(sql, (date_str,)).fetchone()
        return _row_to_summary(row, date_str)

    def summary_by_month(self, year: int, month: int) -> Dict:
        """Tổng hợp theo tháng."""
        month_str = f"{year:04d}-{month:02d}"
        sql = """
            SELECT
                SUM(a.banana_green)    AS total_green,
                SUM(a.banana_turning)  AS total_turning,
                SUM(a.banana_ripe)     AS total_ripe,
                SUM(a.banana_overripe) AS total_overripe,
                SUM(a.total_count)     AS grand_total,
                COUNT(DISTINCT a.session_id) AS session_count
            FROM scan_analytics a
            JOIN scan_sessions s ON a.session_id = s.id
            WHERE strftime('%Y-%m', s.started_at) = ?
        """
        with get_connection(self._db_path) as conn:
            row = conn.execute(sql, (month_str,)).fetchone()
        return _row_to_summary(row, month_str)

    def list_for_report(self, session_ids: List[int]) -> List[Dict]:
        """Dữ liệu đầy đủ để xuất báo cáo (join session + user + analytics)."""
        if not session_ids:
            return []
        placeholders = ",".join("?" * len(session_ids))
        sql = f"""
            SELECT
                s.batch_code,
                s.started_at,
                s.ended_at,
                s.source_type,
                s.source_detail,
                u.full_name       AS operator_name,
                u.employee_id     AS operator_employee_id,
                a.banana_green,
                a.banana_turning,
                a.banana_ripe,
                a.banana_overripe,
                a.total_count,
                a.quality_rate
            FROM scan_analytics a
            JOIN scan_sessions s ON a.session_id = s.id
            JOIN users u         ON s.operator_id = u.id
            WHERE a.session_id IN ({placeholders})
            ORDER BY s.started_at
        """
        with get_connection(self._db_path) as conn:
            rows = conn.execute(sql, session_ids).fetchall()
        return [dict(r) for r in rows]


def _row_to_analytics(row: sqlite3.Row) -> ScanAnalytics:
    return ScanAnalytics(
        id=row["id"],
        session_id=row["session_id"],
        banana_green=row["banana_green"],
        banana_turning=row["banana_turning"],
        banana_ripe=row["banana_ripe"],
        banana_overripe=row["banana_overripe"],
        total_count=row["total_count"],
        quality_rate=row["quality_rate"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else None,
    )


def _row_to_summary(row: sqlite3.Row, period: str) -> Dict:
    if row is None:
        return {"period": period, "grand_total": 0, "session_count": 0}
    grand_total = row["grand_total"] or 0
    ripe = row["total_ripe"] or 0
    turning = row["total_turning"] or 0
    quality_rate = round((ripe + turning) / grand_total * 100, 2) if grand_total else 0.0
    return {
        "period": period,
        "banana_green": row["total_green"] or 0,
        "banana_turning": turning,
        "banana_ripe": ripe,
        "banana_overripe": row["total_overripe"] or 0,
        "grand_total": grand_total,
        "quality_rate": quality_rate,
        "session_count": row["session_count"] or 0,
    }