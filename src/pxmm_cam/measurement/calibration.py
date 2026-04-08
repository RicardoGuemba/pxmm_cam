"""Current calibration state: scale px/mm and mm/px."""


class CalibrationState:
    """Holds current scale (px per mm and mm per px) from last 2-click + mm input."""

    def __init__(self) -> None:
        self._scale_px_per_mm: float | None = None
        self._scale_mm_per_px: float | None = None

    def set_from_measurement(self, distance_px: float, distance_mm: float) -> None:
        if distance_mm <= 0:
            raise ValueError("Distância em mm deve ser positiva")
        self._scale_px_per_mm = distance_px / distance_mm
        self._scale_mm_per_px = distance_mm / distance_px

    @property
    def scale_px_per_mm(self) -> float | None:
        return self._scale_px_per_mm

    @property
    def scale_mm_per_px(self) -> float | None:
        return self._scale_mm_per_px

    def has_calibration(self) -> bool:
        return self._scale_px_per_mm is not None and self._scale_mm_per_px is not None
