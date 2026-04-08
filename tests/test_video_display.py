"""Test: frame from worker thread reaches VideoWidget and is displayed."""

import sys
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QThread, Qt, Slot
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pxmm_cam.streaming.capture_worker import CaptureWorker
from pxmm_cam.streaming.frame_source import FrameSource, FrameSourceStatus
from pxmm_cam.ui.video_widget import VideoWidget


class OneFrameSource(FrameSource):
    """Fonte que abre e devolve um único frame BGR válido."""

    def __init__(self):
        self._opened = False
        self._frame = np.zeros((240, 320, 3), dtype=np.uint8)
        self._frame[:] = (120, 60, 60)

    def open(self):
        self._opened = True

    def read_frame(self):
        if not self._opened:
            return None, None
        self._opened = False
        return self._frame.copy(), 0.0

    def close(self):
        self._opened = False

    def get_status(self):
        return FrameSourceStatus(connected=True, backend="Test")


class FrameReceiver(QObject):
    """Objeto na thread principal para receber frames (garante QueuedConnection)."""
    def __init__(self, widget):
        super().__init__()
        self._widget = widget
        self.frames_received = []

    @Slot(object, float)
    def on_frame(self, frame, fps):
        self.frames_received.append((frame is not None, fps))
        self._widget.set_frame(frame)


def test_frame_reaches_widget():
    app = QApplication.instance() or QApplication(sys.argv)
    widget = VideoWidget()
    widget.resize(400, 300)
    receiver = FrameReceiver(widget)

    source = OneFrameSource()
    worker = CaptureWorker(source)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.frame_ready.connect(receiver.on_frame, Qt.ConnectionType.QueuedConnection)
    worker.start_capture()
    thread.start()

    deadline = time.monotonic() + 3.0
    while len(receiver.frames_received) < 1 and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)

    worker.stop_capture()
    thread.quit()
    thread.wait(1000)

    assert len(receiver.frames_received) >= 1, "Nenhum frame recebido no slot"
    assert receiver.frames_received[0][0] is True, "Frame era None"
    assert widget._current_image is not None, "VideoWidget não armazenou a imagem"
    assert widget._current_image.width() == 320 and widget._current_image.height() == 240
    print("OK: frame da thread chegou ao widget e foi armazenado")


if __name__ == "__main__":
    test_frame_reaches_widget()
