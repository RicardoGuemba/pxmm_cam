"""Diagnostic tab: checklist (OS, Python, OpenCV, GStreamer, Harvester, GenTL, ping) and last error."""

import platform
import subprocess
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QGridLayout,
)


def _check_opencv_gstreamer() -> bool:
    try:
        import cv2
        return cv2.getBuildInformation().count("GStreamer") > 0
    except Exception:
        return False


def _check_harvester() -> bool:
    try:
        import harvester  # noqa: F401
        return True
    except ImportError:
        return False


def _check_gentl_loadable(gentl_path: Optional[str] = None) -> bool:
    if not gentl_path or not gentl_path.strip():
        return False
    try:
        import harvester
        h = harvester.Harvester()
        h.add_file(gentl_path.strip())
        return True
    except Exception:
        return False


def _ping_ip(ip: str, timeout_s: float = 2.0) -> str:
    if not ip or not ip.strip():
        return "N/A"
    try:
        param = "-n" if platform.system() == "Windows" else "-c"
        r = subprocess.run(
            ["ping", param, "1", ip.strip()],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return "Alcançável" if r.returncode == 0 else "Inacessível"
    except Exception as e:
        return str(e)


class DiagnosticTab(QWidget):
    """Tab with environment checklist and last error log."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox("Ambiente")
        grid = QGridLayout(group)
        row = 0
        grid.addWidget(QLabel("SO:"), row, 0)
        grid.addWidget(QLabel(f"{platform.system()} {platform.release()}"), row, 1)
        row += 1
        grid.addWidget(QLabel("Python:"), row, 0)
        grid.addWidget(QLabel(sys.version.split()[0]), row, 1)
        row += 1
        try:
            import cv2
            grid.addWidget(QLabel("OpenCV:"), row, 0)
            grid.addWidget(QLabel(cv2.__version__), row, 1)
        except Exception:
            grid.addWidget(QLabel("OpenCV:"), row, 0)
            grid.addWidget(QLabel("Não instalado"), row, 1)
        row += 1
        grid.addWidget(QLabel("OpenCV + GStreamer:"), row, 0)
        grid.addWidget(QLabel("Sim" if _check_opencv_gstreamer() else "Não"), row, 1)
        row += 1
        grid.addWidget(QLabel("Harvester instalado:"), row, 0)
        grid.addWidget(QLabel("Sim" if _check_harvester() else "Não"), row, 1)
        row += 1
        grid.addWidget(QLabel("GenTL Producer carregável:"), row, 0)
        gentl_ok = "N/A"
        try:
            from pxmm_cam.config import load_config
            c = load_config()
            gentl_ok = "Sim" if _check_gentl_loadable(c.streaming.gentl_producer_path) else "Não"
        except Exception:
            pass
        grid.addWidget(QLabel(gentl_ok), row, 1)
        row += 1
        layout.addWidget(group)

        self._ping_label = QLabel("Ping (IP): N/A")
        layout.addWidget(self._ping_label)

        group2 = QGroupBox("Último erro")
        self._error_text = QTextEdit()
        self._error_text.setReadOnly(True)
        self._error_text.setMaximumHeight(120)
        group2_layout = QVBoxLayout(group2)
        group2_layout.addWidget(self._error_text)
        layout.addWidget(group2)

        self._refresh()

    def _refresh(self) -> None:
        # Ping: could be taken from main window's GigE IP if needed
        self._ping_label.setText("Ping: configure IP na aba Operação (GigE) e reconecte para testar.")

    def set_last_error(self, text: str) -> None:
        self._error_text.setPlainText(text)

    def set_ping_result(self, ip: str, result: str) -> None:
        self._ping_label.setText(f"Ping ({ip}): {result}")
