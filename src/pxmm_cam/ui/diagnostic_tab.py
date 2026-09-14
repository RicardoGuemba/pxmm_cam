"""Diagnostic tab: checklist (OS, Python, OpenCV, stapipy/SentechSDK, ping) and last error."""

import platform
import sys
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QGridLayout,
)


def _check_stapipy() -> Tuple[bool, str]:
    try:
        import stapipy  # noqa: F401
        return True, "Importável"
    except ImportError:
        return False, "Não instalado (wheel local, não PyPI)"
    except Exception as e:
        return False, str(e)


def _check_sentech_sdk() -> Tuple[bool, str]:
    candidates = [
        Path("/opt/sentech"),
        Path("/opt/SentechSDK"),
        Path("/opt/omron/sentech"),
    ]
    for p in candidates:
        if p.is_dir():
            return True, str(p)
    return False, "Não encontrado (ex.: /opt/sentech)"


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
        stapipy_ok, stapipy_msg = _check_stapipy()
        grid.addWidget(QLabel("stapipy (StApi):"), row, 0)
        grid.addWidget(QLabel("Sim — " + stapipy_msg if stapipy_ok else "Não — " + stapipy_msg), row, 1)
        row += 1
        sdk_ok, sdk_msg = _check_sentech_sdk()
        grid.addWidget(QLabel("SentechSDK:"), row, 0)
        grid.addWidget(QLabel("Sim — " + sdk_msg if sdk_ok else "Não — " + sdk_msg), row, 1)
        row += 1
        hint = QLabel(
            "Abertura da Sentech: StApi (enumeração), não Harvester/.cti. "
            "Feche o StViewer se o device estiver ocupado. Confira .stprofile do SDK."
        )
        hint.setWordWrap(True)
        grid.addWidget(hint, row, 0, 1, 2)
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
        self._ping_label.setText(
            "Ping: IP no yaml é só diagnóstico; StApi não abre por gige://IP."
        )

    def set_last_error(self, text: str) -> None:
        self._error_text.setPlainText(text)

    def set_ping_result(self, ip: str, result: str) -> None:
        self._ping_label.setText(f"Ping ({ip}): {result}")
