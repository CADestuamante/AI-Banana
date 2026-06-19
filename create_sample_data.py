"""
Tạo sample data để test History tab.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import datetime, timedelta, timezone
from banana_ai.database.connection import get_connection

DB_PATH = "data/processed/banana_ai.db"

def create_sample_data():
    with get_connection(DB_PATH) as conn:
        # Lấy user operator (ID = 2)
        user = conn.execute("SELECT id FROM users WHERE username = 'operator'").fetchone()
        if not user:
            print("❌ Không tìm thấy user 'operator'")
            return
        
        operator_id = user["id"]
        now = datetime.now(timezone.utc)
        
        # Tạo 3 phiên quét sample
        sessions_data = [
            (f"ME_20260618_01", operator_id, "camera", "Camera_01", 
             now - timedelta(hours=3), now - timedelta(hours=2)),
            (f"ME_20260618_02", operator_id, "file", "video_sample.mp4", 
             now - timedelta(hours=1), now - timedelta(minutes=30)),
            (f"ME_20260617_01", operator_id, "camera", "Camera_01", 
             now - timedelta(days=1, hours=2), now - timedelta(days=1, hours=1)),
        ]
        
        for batch_code, op_id, source_type, source_detail, started, ended in sessions_data:
            # Chèn session
            cursor = conn.execute("""
                INSERT OR IGNORE INTO scan_sessions 
                (batch_code, operator_id, source_type, source_detail, started_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (batch_code, op_id, source_type, source_detail, 
                  started.isoformat(), ended.isoformat()))
            
            session_id = cursor.lastrowid
            
            # Chèn analytics cho mỗi session
            conn.execute("""
                INSERT INTO scan_analytics 
                (session_id, banana_green, banana_turning, banana_ripe, banana_overripe, 
                 total_count, quality_rate, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, 15, 32, 95, 8, 150, 84.7, now.isoformat()))
        
        conn.commit()
        print(f"✅ Tạo sample data thành công! 3 phiên quét được thêm vào database.")

if __name__ == "__main__":
    create_sample_data()
