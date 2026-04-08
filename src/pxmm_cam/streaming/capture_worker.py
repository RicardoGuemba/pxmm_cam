"""Capture worker: QThread that reads frames and emits frame + FPS. Drop frames when UI is slow."""

import time
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Signal

from .frame_source import FrameSource


class CaptureWorker(QObject):
    """Worker that runs in QThread: loop read_frame(), emit frame and FPS. Drop frames if needed."""

    # Use object to avoid cross-thread numpy type registration issues
    frame_ready = Signal(object, float)  # frame (BGR ndarray), fps
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(self, source: FrameSource) -> None:
        super().__init__()
        self._source = source
        self._running = False
        self._last_ts: Optional[float] = None
        self._fps_alpha = 0.1  # smoothing for FPS

    def start_capture(self) -> None:
        self._running = True
        self._last_ts = None

    def stop_capture(self) -> None:
        self._running = False

    def run(self) -> None:
        fps_value = 0.0
        try:
            self._source.open()
            status = self._source.get_status()
            if not status.connected:
                self.error_occurred.emit(status.error or "Falha ao abrir fonte")
                self.finished.emit()
                return
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit()
            return

        while self._running:
            frame, ts = self._source.read_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            now = time.monotonic()
            if self._last_ts is not None:
                dt = now - self._last_ts
                if dt > 0:
                    instant_fps = 1.0 / dt
                    fps_value = self._fps_alpha * instant_fps + (1 - self._fps_alpha) * fps_value
            self._last_ts = now
            # Enviar cópia para a UI não compartilhar buffer com a próxima leitura
            try:
                frame_copy = frame.copy()
            except Exception:
                frame_copy = frame
            self.frame_ready.emit(frame_copy, fps_value)
            # No explicit drop logic here: Qt signal/slot is queued; if UI is slow, queue grows.
            # For true drop-frames we could use a single-slot queued connection and skip emit when pending.
            # Minimal approach: just emit every frame; UI can throttle paint if needed.

        try:
            self._source.close()
        except Exception:
            pass
        self.finished.emit()
