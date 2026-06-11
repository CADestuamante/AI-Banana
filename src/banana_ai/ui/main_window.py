"""Main application window — Operator + Admin view (PySide6).

Layout:
  topbar
  QTabWidget:
    Tab 0 "Quét" (tất cả):    camera_panel | stats_panel
    Tab 1 "Lịch sử" (manager): bảng session
    Tab 2 "Quản lý" (admin):   quản lý user
  bottombar
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from PySide6.QtCore import (
    QElapsedTimer,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from banana_ai.auth.models import Role, User
from banana_ai.config import AppConfig
from banana_ai.inference.predictor import Prediction

# ── Class definitions ────────────────────────────────────────────────────────

# Label YOLO → màu hiển thị
# Keys phải khớp với model.names của file best.pt đã train
CLASS_COLORS: Dict[str, str] = {
    "unripe":   "#4CAF50",   # Xanh (chưa chín)
    "turning":  "#FF9800",   # Sắp chín
    "ripe":     "#F5A623",   # Chín vàng đạt chuẩn
    "overripe": "#E24B4A",   # Chín quá / Hỏng
}

CLASS_LABELS: Dict[str, str] = {
    "unripe":   "Xanh (chưa chín)",
    "turning":  "Sắp chín",
    "ripe":     "Chín vàng",
    "overripe": "Chín quá / Hỏng",
}

CLASS_TO_DB_FIELD: Dict[str, str] = {
    "unripe":   "banana_green",
    "turning":  "banana_turning",
    "ripe":     "banana_ripe",
    "overripe": "banana_overripe",
}

DEFAULT_COLOR = "#888888"


def _hex_to_qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)


def _elapsed_str(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ── Camera feed widget ────────────────────────────────────────────────────────

class CameraFeedWidget(QLabel):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(480, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: #111111; border-radius: 8px;")
        self._predictions: List[Prediction] = []
        self._base_pixmap: Optional[QPixmap] = None
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        pm = QPixmap(640, 480)
        pm.fill(QColor("#111111"))
        painter = QPainter(pm)
        painter.setPen(QColor("#444444"))
        painter.setFont(QFont("Segoe UI", 14))
        painter.drawText(pm.rect(), Qt.AlignCenter, "Chưa có tín hiệu\nChọn nguồn để bắt đầu")
        painter.end()
        self.setPixmap(pm.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_frame(self, frame_pixmap: QPixmap, predictions: List[Prediction]) -> None:
        self._base_pixmap = frame_pixmap
        self._predictions = predictions
        self._repaint_with_boxes()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._base_pixmap:
            self._repaint_with_boxes()

    def _repaint_with_boxes(self) -> None:
        if not self._base_pixmap:
            return
        scaled = self._base_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(scaled)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        sx = scaled.width() / self._base_pixmap.width()
        sy = scaled.height() / self._base_pixmap.height()
        for pred in self._predictions:
            if len(pred.box) < 4:
                continue
            x1, y1, x2, y2 = pred.box[:4]
            dx, dy = int(x1 * sx), int(y1 * sy)
            dw, dh = int((x2 - x1) * sx), int((y2 - y1) * sy)
            color = _hex_to_qcolor(CLASS_COLORS.get(pred.label, DEFAULT_COLOR))
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(dx, dy, dw, dh, 4, 4)
            label_text = f"{CLASS_LABELS.get(pred.label, pred.label)}  {pred.confidence:.0%}"
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label_text) + 10
            th = fm.height() + 4
            painter.fillRect(dx, dy - th, tw, th, color)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(dx + 5, dy - 4, label_text)
        painter.end()
        self.setPixmap(canvas)


# ── Class row ─────────────────────────────────────────────────────────────────

class ClassRowWidget(QWidget):
    def __init__(self, label: str, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(3)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        dot.setFixedWidth(14)
        self._name_lbl = QLabel(label)
        self._name_lbl.setStyleSheet("font-size: 12px;")
        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        self._count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(dot)
        top.addWidget(self._name_lbl, 1)
        top.addWidget(self._count_lbl)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(
            f"QProgressBar {{ background: #E8E8E8; border-radius: 2px; border: none; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
        )
        root.addLayout(top)
        root.addWidget(self._bar)

    def set_value(self, count: int, total: int) -> None:
        self._count_lbl.setText(str(count))
        self._bar.setValue(int(count * 100 / total) if total > 0 else 0)


# ── Metric card ───────────────────────────────────────────────────────────────

class MetricCard(QFrame):
    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: #F5F5F5; border-radius: 8px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        self._val = QLabel("—")
        self._val.setStyleSheet("font-size: 20px; font-weight: 600; color: #1a1a1a;")
        self._lbl = QLabel(label)
        self._lbl.setStyleSheet("font-size: 10px; color: #888888;")
        layout.addWidget(self._val)
        layout.addWidget(self._lbl)

    def set_value(self, text: str, color: str = "#1a1a1a") -> None:
        self._val.setText(text)
        self._val.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {color};")


# ── Stats panel ───────────────────────────────────────────────────────────────

class StatsPanel(QScrollArea):
    confidence_changed = Signal(float)

    def __init__(self, user: User, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._user = user
        self.setFixedWidth(244)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: white; }")
        inner = QWidget()
        self.setWidget(inner)
        root = QVBoxLayout(inner)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._section_label("Phiên này"))
        grid_w = QWidget()
        grid = QHBoxLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        self._card_total   = MetricCard("Tổng đã phát hiện")
        self._card_frame   = MetricCard("Trong khung")
        self._card_latency = MetricCard("Độ trễ TB")
        self._card_conf    = MetricCard("Độ tin cậy TB")
        left_col.addWidget(self._card_total)
        left_col.addWidget(self._card_latency)
        right_col.addWidget(self._card_frame)
        right_col.addWidget(self._card_conf)
        grid.addLayout(left_col)
        grid.addLayout(right_col)
        root.addWidget(grid_w)

        root.addWidget(self._section_label("Theo loại"))
        self._class_rows: Dict[str, ClassRowWidget] = {}
        for cls, color in CLASS_COLORS.items():
            row = ClassRowWidget(CLASS_LABELS[cls], color)
            self._class_rows[cls] = row
            root.addWidget(row)

        # ── Confidence threshold — chỉ Manager/Admin mới chỉnh được ──
        root.addWidget(self._section_label("Ngưỡng nhận diện"))
        conf_header = QHBoxLayout()
        conf_header.addWidget(QLabel("Ngưỡng tối thiểu"))
        self._conf_val_lbl = QLabel("0.40")
        self._conf_val_lbl.setStyleSheet("font-weight: 600;")
        conf_header.addStretch()
        conf_header.addWidget(self._conf_val_lbl)
        root.addLayout(conf_header)

        self._conf_slider = QSlider(Qt.Horizontal)
        self._conf_slider.setRange(0, 100)
        self._conf_slider.setValue(40)
        self._conf_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: #E0E0E0; border-radius: 2px; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; margin: -5px 0;"
            "  background: #F5A623; border-radius: 7px; }"
            "QSlider::sub-page:horizontal { background: #F5A623; border-radius: 2px; }"
        )
        self._conf_slider.valueChanged.connect(self._on_conf_changed)

        # Phân quyền: operator chỉ xem, không chỉnh được
        if not user.can_configure:
            self._conf_slider.setEnabled(False)
            self._conf_slider.setToolTip("Chỉ Manager/Admin mới được thay đổi ngưỡng")
            lock_lbl = QLabel("🔒 Chỉ Manager mới thay đổi được")
            lock_lbl.setStyleSheet("color: #aaa; font-size: 10px; font-style: italic;")
            root.addWidget(lock_lbl)

        root.addWidget(self._conf_slider)

        self._alert = QLabel("")
        self._alert.setWordWrap(True)
        self._alert.setStyleSheet(
            "background: #FFF3CD; color: #856404; border-radius: 6px; padding: 8px 10px; font-size: 11px;"
        )
        self._alert.hide()
        root.addWidget(self._alert)
        root.addStretch()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 0.06em; color: #888888;")
        return lbl

    @Slot(int)
    def _on_conf_changed(self, value: int) -> None:
        threshold = value / 100.0
        self._conf_val_lbl.setText(f"{threshold:.2f}")
        self.confidence_changed.emit(threshold)

    def update_stats(self, predictions: List[Prediction], total_detected: int,
                     avg_latency_ms: float, overripe_spike: bool) -> None:
        counts: Dict[str, int] = {cls: 0 for cls in CLASS_COLORS}
        total_conf = 0.0
        for p in predictions:
            if p.label in counts:
                counts[p.label] += 1
            total_conf += p.confidence
        in_frame = len(predictions)
        avg_conf = (total_conf / in_frame * 100) if in_frame > 0 else 0
        self._card_total.set_value(str(total_detected))
        self._card_frame.set_value(str(in_frame))
        self._card_latency.set_value(
            f"{avg_latency_ms:.1f} ms",
            color="#D4930A" if avg_latency_ms > 100 else "#1a1a1a",
        )
        self._card_conf.set_value(f"{avg_conf:.0f}%")
        total_in_frame = max(in_frame, 1)
        for cls, row in self._class_rows.items():
            row.set_value(counts[cls], total_in_frame)
        if overripe_spike:
            self._alert.setText(f"⚠  {counts['overripe']} chuối hỏng phát hiện gần đây")
            self._alert.show()
        else:
            self._alert.hide()


# ── History tab (Manager/Admin) ───────────────────────────────────────────────

class HistoryTab(QWidget):
    """Tab xem lịch sử phiên quét và xuất báo cáo."""

    def __init__(self, db_path: str, user: User, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._user = user
        self._build_ui()
        self._load_sessions()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Lịch sử phiên quét")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        btn_refresh = QPushButton("🔄  Làm mới")
        btn_refresh.setFixedHeight(30)
        btn_refresh.setStyleSheet(self._btn_style())
        btn_refresh.clicked.connect(self._load_sessions)
        toolbar.addWidget(btn_refresh)

        if self._user.can_export:
            btn_export = QPushButton("📥  Xuất báo cáo")
            btn_export.setFixedHeight(30)
            btn_export.setStyleSheet(self._btn_primary_style())
            btn_export.clicked.connect(self._export_report)
            toolbar.addWidget(btn_export)

        root.addLayout(toolbar)

        # Filter
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Lọc theo ngày:"))
        self._filter_date = QLineEdit()
        self._filter_date.setPlaceholderText("YYYY-MM-DD (để trống = tất cả)")
        self._filter_date.setFixedWidth(180)
        self._filter_date.setFixedHeight(28)
        filter_bar.addWidget(self._filter_date)
        btn_filter = QPushButton("Lọc")
        btn_filter.setFixedHeight(28)
        btn_filter.setStyleSheet(self._btn_style())
        btn_filter.clicked.connect(self._load_sessions)
        filter_bar.addWidget(btn_filter)
        filter_bar.addStretch()
        root.addLayout(filter_bar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Mã mẻ hàng", "Operator", "Nguồn", "Bắt đầu", "Kết thúc",
            "Tổng chuối", "Tỷ lệ đạt chuẩn",
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget { border: 1px solid #E8E8E8; border-radius: 6px; }"
            "QHeaderView::section { background: #F5F5F5; font-weight: 600; padding: 6px; }"
        )
        root.addWidget(self._table)

        # Summary bar
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet("color: #666; font-size: 11px;")
        root.addWidget(self._summary_lbl)

    def _load_sessions(self) -> None:
        from banana_ai.database import SessionRepository, AnalyticsRepository
        session_repo = SessionRepository(self._db_path)
        analytics_repo = AnalyticsRepository(self._db_path)
        from banana_ai.database import UserRepository
        user_repo = UserRepository(self._db_path)

        date_filter = self._filter_date.text().strip() if hasattr(self, "_filter_date") else ""
        if date_filter:
            sessions = session_repo.list_by_date(date_filter)
        else:
            sessions = session_repo.list_all(limit=200)

        self._table.setRowCount(len(sessions))
        for row_idx, sess in enumerate(sessions):
            # Operator name
            op_user = user_repo.get_by_id(sess.operator_id)
            op_name = op_user.full_name if op_user else str(sess.operator_id)

            # Analytics
            analytics = analytics_repo.get_by_session(sess.id)
            total = analytics.total_count if analytics else 0
            quality = f"{analytics.quality_rate:.1f}%" if analytics else "—"

            started = sess.started_at.strftime("%d/%m/%Y %H:%M") if sess.started_at else "—"
            ended   = sess.ended_at.strftime("%H:%M") if sess.ended_at else "Đang chạy"

            cells = [sess.batch_code, op_name, sess.source_type,
                     started, ended, str(total), quality]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row_idx, col, item)

        self._summary_lbl.setText(f"Hiển thị {len(sessions)} phiên")

    def _export_report(self) -> None:
        from banana_ai.database import SessionRepository, AnalyticsRepository
        session_repo = SessionRepository(self._db_path)
        analytics_repo = AnalyticsRepository(self._db_path)

        date_filter = self._filter_date.text().strip()
        if date_filter:
            sessions = session_repo.list_by_date(date_filter)
        else:
            sessions = session_repo.list_all(limit=200)

        if not sessions:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu để xuất.")
            return

        session_ids = [s.id for s in sessions]
        rows = analytics_repo.list_for_report(session_ids)

        save_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Lưu báo cáo", f"baocao_{date.today()}.csv",
            "CSV files (*.csv);;Excel files (*.xlsx)",
        )
        if not save_path:
            return

        try:
            if save_path.endswith(".xlsx"):
                self._export_xlsx(rows, save_path)
            else:
                self._export_csv(rows, save_path)
            QMessageBox.information(self, "Thành công", f"Đã xuất báo cáo:\n{save_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể xuất báo cáo:\n{exc}")

    @staticmethod
    def _export_csv(rows: list, path: str) -> None:
        import csv
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _export_xlsx(rows: list, path: str) -> None:
        import pandas as pd
        df = pd.DataFrame(rows)
        df.to_excel(path, index=False)

    @staticmethod
    def _btn_style() -> str:
        return (
            "QPushButton { border: 1px solid #DDDDDD; border-radius: 6px;"
            "  padding: 0 12px; font-size: 12px; color: #444; background: white; }"
            "QPushButton:hover { background: #F5F5F5; }"
        )

    @staticmethod
    def _btn_primary_style() -> str:
        return (
            "QPushButton { border: none; border-radius: 6px; padding: 0 14px;"
            "  font-size: 12px; background: #F5A623; color: white; font-weight: 600; }"
            "QPushButton:hover { background: #e09510; }"
        )


# ── User management tab (Admin only) ─────────────────────────────────────────

class UserManagementTab(QWidget):
    """Tab quản lý tài khoản — chỉ Admin."""

    def __init__(self, db_path: str, current_user: User,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._current_user = current_user
        self._build_ui()
        self._load_users()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Quản lý tài khoản")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        root.addWidget(title)

        # ── Thêm user mới ─────────────────────────────────────────────
        add_frame = QFrame()
        add_frame.setStyleSheet(
            "QFrame { background: #F9F9F9; border: 1px solid #E8E8E8; border-radius: 8px; }"
        )
        add_layout = QVBoxLayout(add_frame)
        add_layout.setContentsMargins(14, 12, 14, 12)
        add_layout.setSpacing(8)
        add_title = QLabel("Tạo tài khoản mới")
        add_title.setStyleSheet("font-weight: 600; font-size: 13px;")
        add_layout.addWidget(add_title)

        row1 = QHBoxLayout()
        self._inp_username   = QLineEdit(); self._inp_username.setPlaceholderText("Tên đăng nhập")
        self._inp_password   = QLineEdit(); self._inp_password.setPlaceholderText("Mật khẩu")
        self._inp_password.setEchoMode(QLineEdit.Password)
        self._inp_fullname   = QLineEdit(); self._inp_fullname.setPlaceholderText("Họ và tên")
        self._inp_employeeid = QLineEdit(); self._inp_employeeid.setPlaceholderText("Mã NV (vd: NV-003)")
        for w in [self._inp_username, self._inp_password, self._inp_fullname, self._inp_employeeid]:
            w.setFixedHeight(32)
            w.setStyleSheet(
                "QLineEdit { border: 1px solid #ccc; border-radius: 6px; padding: 0 8px; }"
                "QLineEdit:focus { border-color: #F5A623; }"
            )
            row1.addWidget(w)

        self._inp_role = QComboBox()
        self._inp_role.addItems(["operator", "admin"])
        self._inp_role.setFixedHeight(32)
        row1.addWidget(self._inp_role)

        btn_add = QPushButton("➕  Thêm")
        btn_add.setFixedHeight(32)
        btn_add.setStyleSheet(
            "QPushButton { border: none; border-radius: 6px; padding: 0 16px;"
            "  background: #F5A623; color: white; font-weight: 600; }"
            "QPushButton:hover { background: #e09510; }"
        )
        btn_add.clicked.connect(self._add_user)
        row1.addWidget(btn_add)

        add_layout.addLayout(row1)
        root.addWidget(add_frame)

        # ── Bảng danh sách user ───────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "ID", "Tên đăng nhập", "Họ và tên", "Mã NV", "Vai trò", "Trạng thái", "Thao tác",
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget { border: 1px solid #E8E8E8; border-radius: 6px; }"
            "QHeaderView::section { background: #F5F5F5; font-weight: 600; padding: 6px; }"
        )
        root.addWidget(self._table)

    def _load_users(self) -> None:
        from banana_ai.database import UserRepository
        repo = UserRepository(self._db_path)
        users = repo.list_all()
        self._table.setRowCount(len(users))
        for row_idx, u in enumerate(users):
            cells = [str(u.id), u.username, u.full_name, u.employee_id, u.role, u.status]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 5:  # status
                    item.setForeground(QColor("#2e7d32") if val == "active" else QColor("#c62828"))
                self._table.setItem(row_idx, col, item)

            # Cột thao tác — không cho xóa/khóa chính mình
            action_w = QWidget()
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(4, 2, 4, 2)
            action_lay.setSpacing(4)

            is_self = (u.username == self._current_user.username)
            btn_toggle = QPushButton(
                "🔓 Mở khóa" if u.status == "blocked" else "🔒 Khóa"
            )
            btn_toggle.setFixedHeight(24)
            btn_toggle.setEnabled(not is_self)
            btn_toggle.setStyleSheet(
                "QPushButton { border: 1px solid #ccc; border-radius: 4px; font-size: 11px;"
                "  padding: 0 8px; background: white; }"
                "QPushButton:hover:enabled { background: #FFF3D6; }"
                "QPushButton:disabled { color: #bbb; }"
            )
            uid = u.id
            current_status = u.status
            btn_toggle.clicked.connect(
                lambda _, uid=uid, s=current_status: self._toggle_status(
                    uid, "active" if s == "blocked" else "blocked"
                )
            )
            action_lay.addWidget(btn_toggle)

            btn_del = QPushButton("🗑 Xóa")
            btn_del.setFixedHeight(24)
            btn_del.setEnabled(not is_self)
            btn_del.setStyleSheet(
                "QPushButton { border: 1px solid #ffcdd2; border-radius: 4px; font-size: 11px;"
                "  padding: 0 8px; background: white; color: #c62828; }"
                "QPushButton:hover:enabled { background: #ffebee; }"
                "QPushButton:disabled { color: #bbb; border-color: #eee; }"
            )
            btn_del.clicked.connect(lambda _, uid=uid: self._delete_user(uid))
            action_lay.addWidget(btn_del)

            self._table.setCellWidget(row_idx, 6, action_w)

    def _add_user(self) -> None:
        username    = self._inp_username.text().strip()
        password    = self._inp_password.text()
        full_name   = self._inp_fullname.text().strip()
        employee_id = self._inp_employeeid.text().strip()
        role        = self._inp_role.currentText()

        if not all([username, password, full_name, employee_id]):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền đầy đủ tất cả các trường.")
            return

        from banana_ai.database import UserRepository
        repo = UserRepository(self._db_path)
        try:
            repo.create(username, password, full_name, employee_id, role)
            QMessageBox.information(self, "Thành công", f"Đã tạo tài khoản '{username}'.")
            for w in [self._inp_username, self._inp_password,
                      self._inp_fullname, self._inp_employeeid]:
                w.clear()
            self._load_users()
        except ValueError as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _toggle_status(self, user_id: int, new_status: str) -> None:
        from banana_ai.database import UserRepository
        repo = UserRepository(self._db_path)
        repo.update_status(user_id, new_status)
        action = "mở khóa" if new_status == "active" else "khóa"
        QMessageBox.information(self, "Thành công", f"Đã {action} tài khoản.")
        self._load_users()

    def _delete_user(self, user_id: int) -> None:
        confirm = QMessageBox.question(
            self, "Xác nhận xóa",
            "Bạn có chắc muốn xóa tài khoản này?\nThao tác không thể hoàn tác.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        from banana_ai.database import UserRepository
        repo = UserRepository(self._db_path)
        repo.delete(user_id)
        self._load_users()


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, user: User) -> None:
        super().__init__()
        self.config = config
        self.user = user
        self._total_detected = 0
        self._session_timer = QElapsedTimer()
        self._session_timer.start()
        self._overripe_recent = 0
        self._worker = None
        self._pending_file_path: Optional[str] = None
        self._current_source: str = "camera"
        self._build_ui()
        self._start_session_clock()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"{self.config.app.name} — {self.user.username}")
        self.resize(1100, 700)
        self.setStyleSheet("QMainWindow { background: #F7F7F5; }")
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())
        root.addWidget(self._build_tabs(), 1)
        root.addWidget(self._build_bottombar())

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet("QFrame { background: white; border-bottom: 1px solid #E8E8E8; }")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("🍌  Banana AI")
        logo.setStyleSheet("font-size: 15px; font-weight: 600; color: #1a1a1a;")
        layout.addWidget(logo)

        self._live_badge = QLabel("● TRỰC TIẾP")
        self._live_badge.setStyleSheet(
            "background: #E6F4EA; color: #1E7E34; border-radius: 10px;"
            "padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )
        self._live_badge.hide()
        layout.addWidget(self._live_badge)
        layout.addStretch()

        # Badge vai trò
        role_color = {"operator": "#1565C0", "admin": "#6A1B9A", "manager": "#2E7D32"}
        role_bg    = {"operator": "#E3F2FD", "admin": "#F3E5F5", "manager": "#E8F5E9"}
        rv = self.user.role.value
        role_badge = QLabel(f"  {self.user.username}  ·  {rv.upper()}  ")
        role_badge.setStyleSheet(
            f"background: {role_bg.get(rv, '#eee')}; color: {role_color.get(rv, '#333')};"
            f"border-radius: 10px; padding: 2px 0; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(role_badge)

        logout_btn = QPushButton("Đăng xuất")
        logout_btn.setFixedHeight(28)
        logout_btn.setStyleSheet(
            "QPushButton { border: 1px solid #DDDDDD; border-radius: 6px;"
            "  padding: 0 12px; font-size: 12px; color: #444444; background: white; }"
            "QPushButton:hover { background: #F5F5F5; }"
        )
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)
        return bar

    def _build_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background: #F7F7F5; }"
            "QTabBar::tab { padding: 8px 20px; font-size: 12px; }"
            "QTabBar::tab:selected { font-weight: 600; border-bottom: 2px solid #F5A623; }"
        )

        # Tab 0 — Quét (tất cả mọi role)
        scan_widget = self._build_scan_tab()
        self._tabs.addTab(scan_widget, "📷  Quét")

        # Tab 1 — Lịch sử (chỉ manager/admin)
        if self.user.is_manager:
            history_tab = HistoryTab(
                db_path=self.config.storage.db_path,
                user=self.user,
            )
            self._tabs.addTab(history_tab, "📋  Lịch sử")

        # Tab 2 — Quản lý user (chỉ admin)
        if self.user.can_manage_users:
            user_mgmt_tab = UserManagementTab(
                db_path=self.config.storage.db_path,
                current_user=self.user,
            )
            self._tabs.addTab(user_mgmt_tab, "👥  Quản lý")

        return self._tabs

    def _build_scan_tab(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        cam_panel = QWidget()
        cam_layout = QVBoxLayout(cam_panel)
        cam_layout.setContentsMargins(0, 0, 8, 0)
        cam_layout.setSpacing(8)
        cam_lbl = QLabel("CAMERA / FILE")
        cam_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 600; letter-spacing: 0.06em; color: #888888;"
        )
        cam_layout.addWidget(cam_lbl)
        self._feed = CameraFeedWidget()
        cam_layout.addWidget(self._feed, 1)
        cam_layout.addWidget(self._build_cam_controls())
        layout.addWidget(cam_panel, 1)

        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setStyleSheet("color: #E8E8E8;")
        layout.addWidget(div)

        self._stats = StatsPanel(user=self.user)
        self._stats.confidence_changed.connect(self._on_confidence_changed)
        layout.addWidget(self._stats)
        return container

    def _build_cam_controls(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        btn_style = (
            "QPushButton { border: 1px solid #DDDDDD; border-radius: 6px;"
            "  padding: 0 14px; height: 30px; font-size: 12px;"
            "  background: white; color: #333333; }"
            "QPushButton:hover { background: #F5F5F5; }"
            "QPushButton:checked { background: #FFF3D6; border-color: #D4930A; color: #854F0B; }"
        )
        self._btn_camera = QPushButton("📷  Camera")
        self._btn_camera.setCheckable(True)
        self._btn_camera.setChecked(True)
        self._btn_camera.setStyleSheet(btn_style)
        self._btn_camera.clicked.connect(lambda: self._select_source("camera"))

        self._btn_file = QPushButton("📁  Tệp tin")
        self._btn_file.setCheckable(True)
        self._btn_file.setStyleSheet(btn_style)
        self._btn_file.clicked.connect(lambda: self._select_source("file"))

        self._btn_start = QPushButton("▶  Bắt đầu")
        self._btn_start.setStyleSheet(
            "QPushButton { border: none; border-radius: 6px; padding: 0 14px; height: 30px;"
            "  font-size: 12px; background: #F5A623; color: white; font-weight: 600; }"
            "QPushButton:hover { background: #e09510; }"
        )
        self._btn_start.clicked.connect(self._on_start_stop)

        self._btn_pause = QPushButton("⏸  Tạm dừng")
        self._btn_pause.setCheckable(True)
        self._btn_pause.setStyleSheet(btn_style)
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause_toggle)

        self._btn_capture = QPushButton("📸  Chụp")
        self._btn_capture.setStyleSheet(btn_style)
        self._btn_capture.setEnabled(False)
        self._btn_capture.clicked.connect(self._on_capture)

        layout.addWidget(self._btn_camera)
        layout.addWidget(self._btn_file)
        layout.addStretch()
        layout.addWidget(self._btn_start)
        layout.addWidget(self._btn_pause)
        layout.addWidget(self._btn_capture)
        return bar

    def _build_bottombar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(32)
        bar.setStyleSheet("QFrame { background: white; border-top: 1px solid #E8E8E8; }")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(20)
        style = "font-size: 11px; color: #888888;"
        self._status_source = QLabel("📷  Chưa chọn nguồn")
        self._status_source.setStyleSheet(style)
        self._status_model = QLabel(
            f"🧠  {self.config.inference.device.upper()} · {self.config.inference.model_path}"
        )
        self._status_model.setStyleSheet(style)
        self._status_session = QLabel("⏱  00:00:00")
        self._status_session.setStyleSheet(style)
        layout.addWidget(self._status_source)
        layout.addWidget(self._status_model)
        layout.addStretch()
        layout.addWidget(self._status_session)
        return bar

    def _start_session_clock(self) -> None:
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_session)
        self._clock_timer.start()

    @Slot()
    def _tick_session(self) -> None:
        elapsed = self._session_timer.elapsed() // 1000
        self._status_session.setText(f"⏱  {_elapsed_str(elapsed)}")

    def _select_source(self, source: str) -> None:
        self._current_source = source
        self._btn_camera.setChecked(source == "camera")
        self._btn_file.setChecked(source == "file")
        if source == "file":
            path, _ = QFileDialog.getOpenFileName(
                self, "Mở ảnh hoặc video", "",
                "Media files (*.png *.jpg *.jpeg *.mp4 *.avi *.mov)",
            )
            if not path:
                self._select_source("camera")
                return
            self._pending_file_path = path
            self._status_source.setText(f"📁  {path}")
        else:
            self._pending_file_path = None
            self._status_source.setText(f"📷  Camera {self.config.input.camera_index}")
        self._live_badge.setVisible(source == "camera")

    def _on_start_stop(self) -> None:
        if self._worker and self._worker.isRunning():
            self._stop_worker()
            self._btn_start.setText("▶  Bắt đầu")
            self._btn_pause.setEnabled(False)
            self._btn_capture.setEnabled(False)
            self._live_badge.hide()
        else:
            self._start_worker()
            self._btn_start.setText("⏹  Dừng")
            self._btn_pause.setEnabled(True)
            self._btn_capture.setEnabled(True)
            if self._current_source == "camera":
                self._live_badge.show()

    def _start_worker(self) -> None:
        from banana_ai.inference.camera_worker import CameraWorker
        self._worker = CameraWorker(
            model_path=self.config.inference.model_path,
            confidence_threshold=self.config.inference.confidence_threshold,
            device=self.config.inference.device,
        )
        if self._current_source == "file" and self._pending_file_path:
            self._worker.set_source(self._pending_file_path)
        else:
            self._worker.set_source(self.config.input.camera_index)
        self._worker.frame_ready.connect(self._on_new_frame)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _stop_worker(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
            self._worker = None

    @Slot(bool)
    def _on_pause_toggle(self, checked: bool) -> None:
        self._btn_pause.setText("▶  Tiếp tục" if checked else "⏸  Tạm dừng")
        if self._worker:
            self._worker.pause() if checked else self._worker.resume()

    @Slot()
    def _on_capture(self) -> None:
        if self._feed._base_pixmap:
            fname = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self._feed._base_pixmap.save(fname)
            QMessageBox.information(self, "Đã chụp", f"Lưu tại: {fname}")

    @Slot(float)
    def _on_confidence_changed(self, threshold: float) -> None:
        if self._worker:
            self._worker.set_confidence(threshold)

    @Slot(str)
    def _on_worker_error(self, msg: str) -> None:
        QMessageBox.warning(self, "Lỗi", msg)
        self._btn_start.setText("▶  Bắt đầu")
        self._btn_pause.setEnabled(False)
        self._btn_capture.setEnabled(False)

    def _on_logout(self) -> None:
        self._stop_worker()
        self.close()
        from banana_ai.ui.login_dialog import LoginDialog
        dlg = LoginDialog()
        if dlg.exec() == QDialog.Accepted and dlg.user:
            win = MainWindow(config=self.config, user=dlg.user)
            win.show()
            QApplication.instance()._main_window = win

    def closeEvent(self, event) -> None:
        self._stop_worker()
        super().closeEvent(event)

    @Slot(QPixmap, list, float)
    def _on_new_frame(self, frame_pixmap: QPixmap, predictions: List[Prediction],
                      latency_ms: float) -> None:
        self._total_detected += len(predictions)
        self._overripe_recent += sum(1 for p in predictions if p.label == "overripe")
        self._feed.update_frame(frame_pixmap, predictions)
        self._stats.update_stats(
            predictions=predictions,
            total_detected=self._total_detected,
            avg_latency_ms=latency_ms,
            overripe_spike=self._overripe_recent > 5,
        )
