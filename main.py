"""Desktop AI Agent – entry point."""
import os
import sys
import tempfile


def main() -> int:
    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    app.setApplicationName("Desktop AI Agent")
    app.setQuitOnLastWindowClosed(False)  # lives in the tray / on hotkeys

    lock = QLockFile(os.path.join(tempfile.gettempdir(), "desktop_ai_agent.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Desktop AI Agent", "The assistant is already running (see the tray icon "
                                "or press your show/hide hotkey).")
        return 0

    from agent import platform_utils as pu
    from agent.config import Config
    from ui.app_controller import AppController
    from ui.icons import make_app_icon
    from ui.theme import stylesheet

    pu.mac_hide_dock_icon()
    app.setWindowIcon(make_app_icon())
    app.setStyleSheet(stylesheet())
    cfg = Config.load()
    ctl = AppController(app, cfg)
    ctl.show_initial()
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
