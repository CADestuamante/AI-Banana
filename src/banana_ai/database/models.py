"""
Database models — định nghĩa cấu trúc tất cả bảng SQLite.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------

@dataclass
class User:
    """Tài khoản nhân viên.

    Attributes:
        id:              Primary key (auto).
        username:        Tên đăng nhập, duy nhất.
        password_hash:   Mật khẩu đã được hash bằng PBKDF2.
        full_name:       Họ và tên đầy đủ.
        employee_id:     Mã số nhân viên (ví dụ: NV-001).
        role:            'admin' hoặc 'operator'.
        status:          'active' hoặc 'blocked'.
        created_at:      Ngày tạo tài khoản (UTC).
    """
    username: str
    password_hash: str
    full_name: str
    employee_id: str
    role: str                       # 'admin' | 'operator'
    status: str = "active"          # 'active' | 'blocked'
    id: Optional[int] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# SCAN SESSIONS
# ---------------------------------------------------------------------------

@dataclass
class ScanSession:
    """Phiên làm việc — mỗi lần nhân viên bấm 'Bắt đầu quét'.

    Attributes:
        id:              Primary key (auto).
        batch_code:      Mã mẻ hàng, ví dụ: ME_20260604_01.
        operator_id:     FK → users.id (người thực hiện ca quét).
        source_type:     'camera' hoặc 'file'.
        source_detail:   Tên camera (Camera_01) hoặc đường dẫn file video.
        started_at:      Thời điểm bắt đầu quét (UTC).
        ended_at:        Thời điểm kết thúc quét (UTC), None nếu đang chạy.
    """
    batch_code: str
    operator_id: int
    source_type: str                # 'camera' | 'file'
    source_detail: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    id: Optional[int] = None


# ---------------------------------------------------------------------------
# SCAN ANALYTICS
# ---------------------------------------------------------------------------

@dataclass
class ScanAnalytics:
    """Kết quả thống kê chất lượng của một phiên quét.

    Attributes:
        id:                  Primary key (auto).
        session_id:          FK → scan_sessions.id.
        banana_green:        Số quả/nải chuối Xanh.
        banana_turning:      Số quả/nải chuối Sắp chín.
        banana_ripe:         Số quả/nải chuối Chín vàng đạt chuẩn.
        banana_overripe:     Số quả/nải chuối Chín quá / Hỏng.
        total_count:         Tổng số lượng chuối đã đi qua vùng quét.
        quality_rate:        % chuối đạt chuẩn thương mại (tự tính).
        recorded_at:         Thời điểm ghi nhận snapshot này (UTC).
    """
    session_id: int
    banana_green: int = 0
    banana_turning: int = 0
    banana_ripe: int = 0
    banana_overripe: int = 0
    total_count: int = 0
    quality_rate: float = 0.0
    id: Optional[int] = None
    recorded_at: Optional[datetime] = None

    def calculate_quality_rate(self) -> float:
        """Tỷ lệ chuối đạt chuẩn thương mại = (ripe + turning) / total."""
        if self.total_count == 0:
            return 0.0
        commercial = self.banana_ripe + self.banana_turning
        return round(commercial / self.total_count * 100, 2)

    def recalculate(self) -> None:
        """Tính lại total_count và quality_rate từ các giá trị hiện tại."""
        self.total_count = (
            self.banana_green
            + self.banana_turning
            + self.banana_ripe
            + self.banana_overripe
        )
        self.quality_rate = self.calculate_quality_rate()