"""USB camera source via OpenCV VideoCapture."""

import re
import subprocess
import sys
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from .frame_source import FrameSource, FrameSourceStatus

# Máximo de índices USB a tentar (0..N) até achar uma câmera que abra
USB_MAX_INDICES = 10
# Frames iniciais a descartar para a câmera estabilizar foco/exposição
USB_WARMUP_FRAMES = 15

# Nomes (substring, case-insensitive) que indicam webcam/câmera integrada — não usar para entrada USB
BUILTIN_CAMERA_PATTERNS = (
    "facetime",
    "face time",
    "integrated",
    "built-in",
    "builtin",
    "câmera do macbook",
    "camera do macbook",
    "macbook pro",
    "macbook air",
    "isp camera",
    "isight",
)


def _apply_focus_and_warmup(cap: cv2.VideoCapture) -> None:
    """Habilita autofocus (se suportado) e descarta frames iniciais para estabilizar."""
    # Autofocus: 1 = ligado (câmeras USB costumam vir com foco fixo ou AF desligado)
    autofocus = getattr(cv2, "CAP_PROP_AUTOFOCUS", None)
    if autofocus is not None:
        try:
            cap.set(autofocus, 1)
        except Exception:
            pass
    # Buffer mínimo para reduzir atraso e pegar frame mais recente
    buf = getattr(cv2, "CAP_PROP_BUFFERSIZE", None)
    if buf is not None:
        try:
            cap.set(buf, 1)
        except Exception:
            pass
    # Descartar frames iniciais para a câmera ajustar foco e exposição
    for _ in range(USB_WARMUP_FRAMES):
        cap.read()


def _is_builtin_camera(device_name: str) -> bool:
    """True se o nome do dispositivo indica webcam/câmera integrada."""
    lower = (device_name or "").strip().lower()
    return any(p in lower for p in BUILTIN_CAMERA_PATTERNS)


def _get_avfoundation_device_names() -> list[tuple[int, str]]:
    """No macOS, lista índices e nomes de vídeo via ffmpeg AVFoundation. [(índice, nome), ...]."""
    result: list[tuple[int, str]] = []
    try:
        out = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = (out.stderr or "") + (out.stdout or "")
        # [AVFoundation indev ...] [0] Nome do dispositivo
        for m in re.finditer(r"\[\s*(\d+)\s*\]\s*(.+)", text):
            idx_str, name = m.group(1), m.group(2).strip()
            if name.lower().startswith("capture screen"):
                continue
            try:
                idx = int(idx_str)
                result.append((idx, name))
            except ValueError:
                continue
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return result


def _external_usb_indices_darwin(max_indices: int) -> list[int]:
    """No macOS: retorna índices de câmeras que não são integradas (por nome)."""
    names = _get_avfoundation_device_names()
    if not names:
        return list(range(1, max_indices))
    external = [idx for idx, name in names if idx < max_indices and not _is_builtin_camera(name)]
    if external:
        return sorted(external)
    return list(range(1, max_indices))


def get_external_usb_indices(max_indices: int = USB_MAX_INDICES) -> list[int]:
    """Índices considerados 'entrada USB externa': no macOS filtra por nome; em outros SO exclui só 0."""
    if sys.platform == "darwin":
        return _external_usb_indices_darwin(max_indices)
    return list(range(1, max_indices))


def detect_usb_camera_indices(
    max_indices: int = USB_MAX_INDICES,
    usb_only: bool = True,
) -> list[int]:
    """Testa índices e retorna os que abriram.
    usb_only=True: apenas câmeras externas (no macOS exclui por nome; em outros exclui índice 0).
    """
    if usb_only:
        allowed = get_external_usb_indices(max_indices)
    else:
        allowed = list(range(max_indices))
    available = []
    for idx in allowed:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            available.append(idx)
            cap.release()
    return sorted(available)


def first_external_usb_index(max_indices: int = USB_MAX_INDICES) -> int | None:
    """Retorna o primeiro índice de câmera USB externa (no macOS exclui integrada por nome)."""
    for idx in get_external_usb_indices(max_indices):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            cap.release()
            return idx
    return None


class USBCameraSource(FrameSource):
    """Frame source for USB cameras using cv2.VideoCapture.

    On open(), tries indices in order (starting from camera_index) until one
    opens successfully, so an external USB camera is found even if the laptop
    webcam is at 0.
    """

    def __init__(
        self,
        camera_index: int = 0,
        requested_width: Optional[int] = None,
        requested_height: Optional[int] = None,
        target_fps: Optional[float] = None,
    ) -> None:
        self._camera_index = camera_index
        self._requested_width = requested_width
        self._requested_height = requested_height
        self._target_fps = target_fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._error: Optional[str] = None
        self._resolved_index: Optional[int] = None  # índice que efetivamente abriu

    def open(self) -> None:
        if self._cap is not None:
            return
        self._error = None
        allowed = get_external_usb_indices(USB_MAX_INDICES)
        if self._camera_index in allowed:
            indices_to_try = [self._camera_index]
        else:
            indices_to_try = allowed
        for idx in indices_to_try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                self._cap = cap
                self._resolved_index = idx
                if self._requested_width is not None:
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._requested_width)
                if self._requested_height is not None:
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._requested_height)
                if self._target_fps is not None:
                    self._cap.set(cv2.CAP_PROP_FPS, self._target_fps)
                _apply_focus_and_warmup(self._cap)
                return
            cap.release()
        self._error = (
            "Nenhuma câmera USB externa encontrada (entrada USB). "
            "Conecte a câmera na porta USB e tente novamente."
        )

    def read_frame(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        if self._cap is None or not self._cap.isOpened():
            return None, None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None, None
        return frame, time.monotonic()

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._error = None

    def get_status(self) -> FrameSourceStatus:
        if self._cap is None or not self._cap.isOpened():
            return FrameSourceStatus(
                connected=False,
                backend="USB (OpenCV)",
                error=self._error or "Desconectado",
            )
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        backend = "USB (OpenCV)"
        if self._resolved_index is not None:
            backend = f"USB (OpenCV) índice {self._resolved_index}"
        return FrameSourceStatus(
            connected=True,
            backend=backend,
            width=w,
            height=h,
            error=self._error,
        )
