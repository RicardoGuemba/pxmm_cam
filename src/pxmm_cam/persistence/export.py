"""Export history to CSV and JSON with fixed schema."""

import csv
import json
from pathlib import Path
from typing import List

from pxmm_cam.measurement.record import MeasurementRecord
from .schema import EXPORT_SCHEMA_FIELDS


def _record_to_row(r: MeasurementRecord) -> dict:
    return {
        "timestamp": r.timestamp.isoformat(),
        "source_type": r.source_type,
        "source_id": r.source_id,
        "point_a_x": r.point_a[0],
        "point_a_y": r.point_a[1],
        "point_b_x": r.point_b[0],
        "point_b_y": r.point_b[1],
        "distance_px": r.distance_px,
        "distance_mm": r.distance_mm,
        "scale_px_per_mm": r.scale_px_per_mm,
        "scale_mm_per_px": r.scale_mm_per_px,
        "session_id": r.session_id,
    }


def export_csv(records: List[MeasurementRecord], path: Path) -> None:
    """Write records to CSV with schema fields as header."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_SCHEMA_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(_record_to_row(r))


def export_json(records: List[MeasurementRecord], path: Path) -> None:
    """Write records to JSON array with fixed schema."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [_record_to_row(r) for r in records]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
