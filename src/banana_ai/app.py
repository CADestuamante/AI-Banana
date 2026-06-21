"""Application entry point."""
from __future__ import annotations

import sys

from banana_ai.config import AppConfig, load_config
from banana_ai.utils.logging import setup_logging


def main() -> None:
    config: AppConfig = load_config()
    setup_logging(config.app.log_level)

    # Khởi tạo DB + seed tài khoản mặc định (phải trước khi tạo QApplication)
    from banana_ai.auth.service import init_auth
    init_auth(config.storage.db_path)

    # Qt app phải được tạo trước bất kỳ QWidget nào
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette, QColor
    app = QApplication(sys.argv)
    app.setApplicationName(config.app.name)
    
    # ── Force light mode (không bị dark mode của VS Code ảnh hưởng) ────
    app.setStyle("Fusion")
    light_palette = QPalette()
    light_palette.setColor(QPalette.Window, QColor(255, 255, 255))
    light_palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.Text, QColor(0, 0, 0))
    light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    light_palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
    light_palette.setColor(QPalette.Link, QColor(0, 102, 204))
    light_palette.setColor(QPalette.Highlight, QColor(76, 175, 80))
    light_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(light_palette)

    # ── Login ──────────────────────────────────────────────────────────
    from PySide6.QtWidgets import QDialog
    from banana_ai.ui.login_dialog import LoginDialog

    dlg = LoginDialog()
    if dlg.exec() != QDialog.Accepted or dlg.user is None:
        sys.exit(0)

    user = dlg.user

    # ── Main window ────────────────────────────────────────────────────
    from banana_ai.ui.main_window import MainWindow
    window = MainWindow(config=config, user=user)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
