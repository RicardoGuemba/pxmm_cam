"""Video widget with overlay and click-to-frame coordinate mapping."""

from typing import List, Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, QRect, QRectF
from PySide6.QtGui import QImage, QPainter, QPen, QColor
from PySide6.QtWidgets import QSizePolicy, QWidget


class VideoWidget(QWidget):
    """Displays frames (BGR), overlay (points A/B, line), and emits frame coordinates on click."""

    # (x, y) in frame coordinates
    point_clicked = Signal(float, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_image: Optional[QImage] = None
        self._frame_size: Optional[Tuple[int, int]] = None  # (width, height) of last frame
        self._points: List[Tuple[float, float]] = []  # in frame coords
        self.setMinimumSize(320, 200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_frame(self, frame_bgr: np.ndarray) -> None:
        """Accept BGR frame (numpy), store for paint and coordinate mapping."""
        if frame_bgr is None or not hasattr(frame_bgr, "shape") or len(frame_bgr.shape) < 2:
            return
        frame_bgr = np.asarray(frame_bgr, dtype=np.uint8).copy()
        if frame_bgr.size == 0:
            return
        h, w = frame_bgr.shape[:2]
        self._frame_size = (w, h)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        if rgb is None or rgb.size == 0:
            return
        h, w, ch = rgb.shape
        if ch != 3:
            return
        bytes_per_line = ch * w
        # Garantir array contíguo para o QImage
        if not rgb.flags["C_CONTIGUOUS"]:
            rgb = np.ascontiguousarray(rgb)
        qi = QImage(
            rgb.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )
        self._current_image = qi.copy()
        self.update()

    def set_points(self, points: List[Tuple[float, float]]) -> None:
        """Set overlay points (in frame coordinates)."""
        self._points = list(points)
        self.update()

    def clear_points(self) -> None:
        self._points.clear()
        self.update()

    def _widget_to_frame(self, x: float, y: float) -> Optional[Tuple[float, float]]:
        if self._frame_size is None or self._current_image is None:
            return None
        fw, fh = self._frame_size
        iw = self._current_image.width()
        ih = self._current_image.height()
        if iw <= 0 or ih <= 0:
            return None
        # Image is scaled to fit widget; find scale and offset
        w, h = self.width(), self.height()
        scale = min(w / iw, h / ih)
        draw_w = iw * scale
        draw_h = ih * scale
        offset_x = (w - draw_w) / 2
        offset_y = (h - draw_h) / 2
        # Click relative to drawn image
        rx = x - offset_x
        ry = y - offset_y
        if rx < 0 or rx > draw_w or ry < 0 or ry > draw_h:
            return None
        # Map to frame
        fx = (rx / draw_w) * fw
        fy = (ry / draw_h) * fh
        return (fx, fy)

    def _frame_to_widget(self, fx: float, fy: float) -> Optional[Tuple[float, float]]:
        if self._frame_size is None or self._current_image is None:
            return None
        fw, fh = self._frame_size
        iw = self._current_image.width()
        ih = self._current_image.height()
        w, h = self.width(), self.height()
        scale = min(w / iw, h / ih)
        draw_w = iw * scale
        draw_h = ih * scale
        offset_x = (w - draw_w) / 2
        offset_y = (h - draw_h) / 2
        rx = (fx / fw) * draw_w
        ry = (fy / fh) * draw_h
        return (offset_x + rx, offset_y + ry)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0))
        if self._current_image is None:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Sem vídeo")
            return
        iw = self._current_image.width()
        ih = self._current_image.height()
        if iw <= 0 or ih <= 0:
            return
        scale = min(w / iw, h / ih)
        draw_w = iw * scale
        draw_h = ih * scale
        x0 = (w - draw_w) / 2
        y0 = (h - draw_h) / 2
        target_rect = QRectF(x0, y0, draw_w, draw_h)
        source_rect = QRect(0, 0, iw, ih)
        painter.drawImage(target_rect, self._current_image, source_rect)

        # Overlay: points and line
        pen = QPen(QColor(0, 255, 0), 2)
        painter.setPen(pen)
        for i, (fx, fy) in enumerate(self._points):
            pt = self._frame_to_widget(fx, fy)
            if pt is None:
                continue
            px, py = int(pt[0]), int(pt[1])
            painter.drawEllipse(px - 5, py - 5, 10, 10)
            painter.drawText(px + 8, py + 4, ["A", "B"][i] if i < 2 else "")
        if len(self._points) >= 2:
            p0 = self._frame_to_widget(self._points[0][0], self._points[0][1])
            p1 = self._frame_to_widget(self._points[1][0], self._points[1][1])
            if p0 and p1:
                painter.drawLine(int(p0[0]), int(p0[1]), int(p1[0]), int(p1[1]))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self._widget_to_frame(event.position().x(), event.position().y())
            if pt is not None:
                self.point_clicked.emit(pt[0], pt[1])
        super().mousePressEvent(event)
