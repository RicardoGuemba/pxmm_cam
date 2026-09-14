"""Application bootstrap: logging, Qt app and main window."""

import sys

from PySide6.QtWidgets import QApplication

from pxmm_cam.logging_config import setup_logging
from pxmm_cam.ui.main_window import MainWindow


def main() -> int:
    """Initialize logging, Qt app and main window, run event loop."""
    setup_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
