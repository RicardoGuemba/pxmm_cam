"""Dialog to input real distance in mm after 2-click measurement."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QDoubleSpinBox,
    QVBoxLayout,
)


class MmDialog(QDialog):
    """Simple dialog: distance in mm (double spin), OK/Cancel."""

    def __init__(self, parent=None, distance_px: float = 0.0) -> None:
        super().__init__(parent)
        self.setWindowTitle("Distância real (mm)")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._mm_spin = QDoubleSpinBox()
        self._mm_spin.setRange(0.001, 1e6)
        self._mm_spin.setDecimals(3)
        self._mm_spin.setValue(10.0)
        self._mm_spin.setSuffix(" mm")
        form.addRow("Distância (mm):", self._mm_spin)
        layout.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_mm(self) -> Optional[float]:
        if self.result() == QDialog.DialogCode.Accepted:
            return self._mm_spin.value()
        return None
