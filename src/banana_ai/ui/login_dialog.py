"""Login dialog (PySide6).

Shows a username / password form.  On success it stores the
authenticated User and closes with QDialog.Accepted.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from banana_ai.auth.models import User
from banana_ai.auth.service import login


class LoginDialog(QDialog):
    """Modal login dialog.

    Usage::

        dlg = LoginDialog()
        if dlg.exec() == QDialog.Accepted:
            user = dlg.user   # authenticated User
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.user: Optional[User] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("Banana AI — Login")
        self.setFixedSize(380, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel("🍌 Banana AI")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("Ripeness Detection System")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888; margin-bottom: 24px;")
        root.addWidget(subtitle)

        root.addSpacing(20)

        # ── Form ───────────────────────────────────────────────────────
        form = QVBoxLayout()
        form.setSpacing(10)

        lbl_user = QLabel("Username")
        lbl_user.setStyleSheet("font-weight: 600;")
        form.addWidget(lbl_user)

        self._username = QLineEdit()
        self._username.setPlaceholderText("Enter username")
        self._username.setFixedHeight(36)
        self._username.setStyleSheet(self._input_style())
        form.addWidget(self._username)

        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet("font-weight: 600; margin-top: 8px;")
        form.addWidget(lbl_pass)

        self._password = QLineEdit()
        self._password.setPlaceholderText("Enter password")
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setFixedHeight(36)
        self._password.setStyleSheet(self._input_style())
        self._password.returnPressed.connect(self._attempt_login)
        form.addWidget(self._password)

        root.addLayout(form)

        # ── Error label ────────────────────────────────────────────────
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e05252; font-size: 12px;")
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.setFixedHeight(20)
        root.addWidget(self._error_label)

        root.addSpacing(12)

        # ── Login button ───────────────────────────────────────────────
        self._btn_login = QPushButton("Login")
        self._btn_login.setFixedHeight(40)
        self._btn_login.setCursor(Qt.PointingHandCursor)
        self._btn_login.setStyleSheet(self._button_style())
        self._btn_login.clicked.connect(self._attempt_login)
        root.addWidget(self._btn_login)

        # ── Hint ───────────────────────────────────────────────────────
        hint = QLabel("Default: operator / operator123  ·  admin / admin123")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #aaa; font-size: 10px; margin-top: 10px;")
        root.addWidget(hint)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _attempt_login(self) -> None:
        username = self._username.text().strip()
        password = self._password.text()

        if not username or not password:
            self._show_error("Please enter username and password.")
            return

        self._btn_login.setEnabled(False)
        self._btn_login.setText("Logging in…")

        user = login(username, password)

        self._btn_login.setEnabled(True)
        self._btn_login.setText("Login")

        if user is None:
            self._show_error("Invalid username or password.")
            self._password.clear()
            self._password.setFocus()
            return

        self.user = user
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    @staticmethod
    def _input_style() -> str:
        return (
            "QLineEdit {"
            "  border: 1px solid #ccc;"
            "  border-radius: 6px;"
            "  padding: 0 10px;"
            "  font-size: 13px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #f5a623;"
            "}"
        )

    @staticmethod
    def _button_style() -> str:
        return (
            "QPushButton {"
            "  background-color: #f5a623;"
            "  color: white;"
            "  border: none;"
            "  border-radius: 8px;"
            "  font-size: 14px;"
            "  font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "  background-color: #e09510;"
            "}"
            "QPushButton:disabled {"
            "  background-color: #ccc;"
            "}"
        )