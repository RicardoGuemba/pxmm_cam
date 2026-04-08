"""In-memory history of measurements."""

from typing import List

from pxmm_cam.measurement.record import MeasurementRecord


class MeasurementHistory:
    """In-memory list of measurement records."""

    def __init__(self) -> None:
        self._records: List[MeasurementRecord] = []
        self._session_id: str | None = None

    def add(self, record: MeasurementRecord) -> None:
        if self._session_id and record.session_id is None:
            record.session_id = self._session_id
        self._records.append(record)

    def clear(self) -> None:
        self._records.clear()

    def records(self) -> List[MeasurementRecord]:
        return list(self._records)

    def set_session_id(self, session_id: str | None) -> None:
        self._session_id = session_id
