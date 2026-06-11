"""Main application window — Operator view (PySide6).

Layout: topbar | split(camera_panel | stats_panel) | bottombar
"""
from __future__ import annotations

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
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from banana_ai.auth.models import User
from banana_ai.config import AppConfig
from banana_ai.inference.predictor import Prediction

CLASS_COLORS: Dict[str, str] = {
    "overripe": "#9C27B0",
    "ripe":     "#4CAF50",
    "rotten":   "#E24B4A",
    "unripe":   "#FF9800",
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
        painter.drawText(pm.rect(), Qt.AlignCenter, "No signal\nSelect a source to begin")
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
            label_text = f"{pred.label}  {pred.confidence:.0%}"
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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(244)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: white; }")
        inner = QWidget()
        self.setWidget(inner)
        root = QVBoxLayout(inner)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._section_label("This session"))
        grid_w = QWidget()
        grid = QHBoxLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        self._card_total   = MetricCard("Total detected")
        self._card_frame   = MetricCard("In frame")
        self._card_latency = MetricCard("Avg latency")
        self._card_conf    = MetricCard("Avg confidence")
        left_col.addWidget(self._card_total)
        left_col.addWidget(self._card_latency)
        right_col.addWidget(self._card_frame)
        right_col.addWidget(self._card_conf)
        grid.addLayout(left_col)
        grid.addLayout(right_col)
        root.addWidget(grid_w)

        root.addWidget(self._section_label("By class"))
        self._class_rows: Dict[str, ClassRowWidget] = {}
        for cls, color in CLASS_COLORS.items():
            row = ClassRowWidget(cls, color)
            self._class_rows[cls] = row
            root.addWidget(row)

        root.addWidget(self._section_label("Confidence threshold"))
        conf_header = QHBoxLayout()
        conf_header.addWidget(QLabel("Min confidence"))
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
                     avg_latency_ms: float, rotten_spike: bool) -> None:
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
        self._card_latency.set_value(f"{avg_latency_ms:.1f} ms",
                                     color="#D4930A" if avg_latency_ms > 100 else "#1a1a1a")
        self._card_conf.set_value(f"{avg_conf:.0f}%")
        total_in_frame = max(in_frame, 1)
        for cls, row in self._class_rows.items():
            row.set_value(counts[cls], total_in_frame)
        if rotten_spike:
            self._alert.setText(f"⚠  {counts['rotten']} Rotten detected in the last 5 min")
            self._alert.show()
        else:
            self._alert.hide()


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, user: User) -> None:
        super().__init__()
        self.config = config
        self.user = user
        self._total_detected = 0
        self._session_timer = QElapsedTimer()
        self._session_timer.start()
        self._rotten_recent = 0
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
        root.addWidget(self._build_main_area(), 1)
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
        self._live_badge = QLabel("● LIVE")
        self._live_badge.setStyleSheet(
            "background: #E6F4EA; color: #1E7E34; border-radius: 10px;"
            "padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )
        self._live_badge.hide()
        layout.addWidget(self._live_badge)
        layout.addStretch()
        role_lbl = QLabel(f"  {self.user.username}  ({self.user.role.value})")
        role_lbl.setStyleSheet("font-size: 12px; color: #666666;")
        layout.addWidget(role_lbl)
        logout_btn = QPushButton("Logout")
        logout_btn.setFixedHeight(28)
        logout_btn.setStyleSheet(
            "QPushButton { border: 1px solid #DDDDDD; border-radius: 6px;"
            "  padding: 0 12px; font-size: 12px; color: #444444; background: white; }"
            "QPushButton:hover { background: #F5F5F5; }"
        )
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)
        return bar

    def _build_main_area(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)
        cam_panel = QWidget()
        cam_layout = QVBoxLayout(cam_panel)
        cam_layout.setContentsMargins(0, 0, 8, 0)
        cam_layout.setSpacing(8)
        cam_lbl = QLabel("CAMERA FEED")
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
        self._stats = StatsPanel()
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
        self._btn_file = QPushButton("📁  File")
        self._btn_file.setCheckable(True)
        self._btn_file.setStyleSheet(btn_style)
        self._btn_file.clicked.connect(lambda: self._select_source("file"))
        self._btn_start = QPushButton("▶  Start")
        self._btn_start.setStyleSheet(
            "QPushButton { border: none; border-radius: 6px; padding: 0 14px; height: 30px;"
            "  font-size: 12px; background: #F5A623; color: white; font-weight: 600; }"
            "QPushButton:hover { background: #e09510; }"
        )
        self._btn_start.clicked.connect(self._on_start_stop)
        self._btn_pause = QPushButton("⏸  Pause")
        self._btn_pause.setCheckable(True)
        self._btn_pause.setStyleSheet(btn_style)
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause_toggle)
        self._btn_capture = QPushButton("📸  Capture")
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
        self._status_source = QLabel("📷  No source")
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
                self, "Open image or video", "",
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
            self._btn_start.setText("▶  Start")
            self._btn_pause.setEnabled(False)
            self._btn_capture.setEnabled(False)
            self._live_badge.hide()
        else:
            self._start_worker()
            self._btn_start.setText("⏹  Stop")
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
        self._btn_pause.setText("▶  Resume" if checked else "⏸  Pause")
        if self._worker:
            self._worker.pause() if checked else self._worker.resume()

    @Slot()
    def _on_capture(self) -> None:
        if self._feed._base_pixmap:
            from datetime import datetime
            fname = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self._feed._base_pixmap.save(fname)
            QMessageBox.information(self, "Captured", f"Saved: {fname}")

    @Slot(float)
    def _on_confidence_changed(self, threshold: float) -> None:
        if self._worker:
            self._worker.set_confidence(threshold)

    @Slot(str)
    def _on_worker_error(self, msg: str) -> None:
        QMessageBox.warning(self, "Error", msg)
        self._btn_start.setText("▶  Start")
        self._btn_pause.setEnabled(False)
        self._btn_capture.setEnabled(False)

    def _on_logout(self) -> None:
        self._stop_worker()
        from PySide6.QtWidgets import QDialog
        from banana_ai.ui.login_dialog import LoginDialog
        self.close()
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
        self._rotten_recent += sum(1 for p in predictions if p.label == "rotten")
        self._feed.update_frame(frame_pixmap, predictions)
        self._stats.update_stats(
            predictions=predictions,
            total_detected=self._total_detected,
            avg_latency_ms=latency_ms,
            rotten_spike=self._rotten_recent > 5,
        )