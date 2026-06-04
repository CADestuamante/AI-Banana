"""
Script demo — kiểm tra toàn bộ database layer.
Chạy từ thư mục gốc: python scripts/demo_database.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from banana_ai.database import (
    AnalyticsRepository, SessionRepository, UserRepository, init_database,
)

DB_PATH = "data/processed/banana_ai.db"


def main() -> None:
    init_database(DB_PATH)
    users = UserRepository(DB_PATH)
    sessions = SessionRepository(DB_PATH)
    analytics = AnalyticsRepository(DB_PATH)

    # Tạo tài khoản
    try:
        admin = users.create("admin", "Admin@123", "Nguyễn Văn Admin", "NV-001", "admin")
        op    = users.create("operator1", "Op@12345", "Trần Thị Bình", "NV-002", "operator")
    except ValueError:
        admin = users.get_by_username("admin")
        op    = users.get_by_username("operator1")

    # Đăng nhập
    logged_in = users.authenticate("operator1", "Op@12345")
    print(f"Đăng nhập: {logged_in.full_name}")

    # Tạo phiên quét
    session = sessions.create(op.id, "camera", "Camera_01")
    print(f"Phiên: {session.batch_code}")

    # Lưu kết quả AI
    result = analytics.save(session.id, banana_green=12, banana_turning=35,
                            banana_ripe=98, banana_overripe=5)
    print(f"Tổng: {result.total_count} | Đạt chuẩn: {result.quality_rate}%")

    # Đóng phiên
    sessions.close_session(session.id)

    # Thống kê ngày
    from datetime import date
    summary = analytics.summary_by_date(date.today().isoformat())
    print(f"Tỷ lệ hôm nay: {summary['quality_rate']}% / {summary['grand_total']} quả")


if __name__ == "__main__":
    main()