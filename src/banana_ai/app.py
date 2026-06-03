"""Application entry point."""
from __future__ import annotations

import sys

from banana_ai.config import AppConfig, load_config
from banana_ai.utils.logging import setup_logging


def main() -> None:
    config: AppConfig = load_config()
    setup_logging(config.app.log_level)

    # Qt app must be created before any QWidget
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(config.app.name)

    # ── Login ──────────────────────────────────────────────────────────
    from PySide6.QtWidgets import QDialog
    from banana_ai.ui.login_dialog import LoginDialog

    dlg = LoginDialog()
    if dlg.exec() != QDialog.Accepted or dlg.user is None:
        # User closed the dialog without logging in
        sys.exit(0)

    user = dlg.user

    # ── Main window (placeholder, will be built in next step) ──────────
    from banana_ai.ui.main_window import MainWindow
    window = MainWindow(config=config, user=user)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()