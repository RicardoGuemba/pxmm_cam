"""Single measurement record for history and export."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MeasurementRecord:
    """One measurement: two points, distance in px, optional mm and scales."""

    timestamp: datetime
    source_type: str  # "usb" | "gige"
    source_id: str    # e.g. "0" for USB index, "192.168.1.10" for GigE
    point_a: tuple[float, float]
    point_b: tuple[float, float]
    distance_px: float
    distance_mm: Optional[float] = None
    scale_px_per_mm: Optional[float] = None
    scale_mm_per_px: Optional[float] = None
    session_id: Optional[str] = None
