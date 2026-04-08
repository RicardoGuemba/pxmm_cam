"""GigE backends: Harvester (GenTL), GStreamer, OpenCV. Each returns a FrameSource or None."""

import time
from typing import Optional, Tuple

import numpy as np

from .frame_source import FrameSource, FrameSourceStatus


def detect_gstreamer_available() -> bool:
    try:
        import cv2
        return "GStreamer" in cv2.getBuildInformation()
    except Exception:
        return False


# --- Harvester backend ---

def try_harvester_backend(
    ip: str,
    port: int,
    gentl_path: Optional[str],
    requested_width: Optional[int],
    requested_height: Optional[int],
    target_fps: Optional[float],
) -> Optional[FrameSource]:
    if not gentl_path or not gentl_path.strip():
        return None
    try:
        import harvester  # optional dependency
    except ImportError:
        return None
    try:
        return HarvesterBackend(ip, port, gentl_path.strip(), requested_width, requested_height, target_fps)
    except Exception:
        return None


class HarvesterBackend(FrameSource):
    """GigE via Harvester/GenICam using GenTL Producer."""

    def __init__(
        self,
        ip: str,
        port: int,
        gentl_path: str,
        requested_width: Optional[int],
        requested_height: Optional[int],
        target_fps: Optional[float],
    ) -> None:
        try:
            import harvester
        except ImportError:
            raise RuntimeError("Harvester não instalado. Instale com: pip install harvester-core")
        self._ip = ip
        self._port = port
        self._gentl_path = gentl_path
        self._requested_width = requested_width
        self._requested_height = requested_height
        self._target_fps = target_fps
        self._harvester = harvester.Harvester()
        self._harvester.add_file(gentl_path)
        self._ia = None
        self._error: Optional[str] = None

    def open(self) -> None:
        self._error = None
        self._harvester.update_device_info_list()
        if not self._harvester.device_info_list:
            self._error = "Nenhum dispositivo GenICam encontrado. Verifique o GenTL Producer e a rede."
            return
        # Prefer device matching our IP
        dev = None
        for info in self._harvester.device_info_list:
            if hasattr(info, "address") and info.address == self._ip:
                dev = info
                break
        if dev is None:
            dev = self._harvester.device_info_list[0]
        self._ia = self._harvester.create_image_acquirer(device_info=dev)
        self._ia.start_image_acquisition()

    def read_frame(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        if self._ia is None:
            return None, None
        try:
            buffer = self._ia.fetch_buffer()
            try:
                component = buffer.payload.components[0]
                data = component.data
                h, w = component.height, component.width
                if component.data_format == "BGR8":
                    frame = data.reshape(h, w, 3).copy()
                else:
                    frame = data.reshape(h, w).copy()
                    import cv2
                    frame = cv2.cvtColor(frame, cv2.COLOR_BAYER_BG2BGR)  # fallback
                return frame, time.monotonic()
            finally:
                buffer.queue()
        except Exception as e:
            self._error = str(e)
            return None, None

    def close(self) -> None:
        if self._ia is not None:
            try:
                self._ia.stop_image_acquisition()
                self._ia.destroy()
            except Exception:
                pass
            self._ia = None
        self._error = None

    def get_status(self) -> FrameSourceStatus:
        connected = self._ia is not None
        return FrameSourceStatus(
            connected=connected,
            backend="Harvester",
            error=self._error,
        )


# --- GStreamer backend ---

def try_gstreamer_backend(
    ip: str,
    port: int,
    requested_width: Optional[int],
    requested_height: Optional[int],
    target_fps: Optional[float],
) -> Optional[FrameSource]:
    if not detect_gstreamer_available():
        return None
    try:
        return GStreamerBackend(ip, port, requested_width, requested_height, target_fps)
    except Exception:
        return None


class GStreamerBackend(FrameSource):
    """GigE via OpenCV with GStreamer pipeline (e.g. rtspsrc or udpsrc)."""

    def __init__(
        self,
        ip: str,
        port: int,
        requested_width: Optional[int],
        requested_height: Optional[int],
        target_fps: Optional[float],
    ) -> None:
        import cv2
        self._ip = ip
        self._port = port
        self._requested_width = requested_width
        self._requested_height = requested_height
        self._target_fps = target_fps
        self._cap = None
        self._error: Optional[str] = None

    def open(self) -> None:
        import cv2
        self._error = None
        pipeline = (
            f"rtspsrc location=rtsp://{self._ip}:{self._port}/ latency=0 ! "
            "decodebin ! videoconvert ! appsink"
        )
        self._cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._cap.isOpened():
            self._error = "Falha ao abrir pipeline GStreamer. Verifique URL e codec."
            if self._cap:
                self._cap.release()
            self._cap = None

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
        connected = self._cap is not None and self._cap.isOpened()
        return FrameSourceStatus(
            connected=connected,
            backend="GStreamer",
            error=self._error,
        )


# --- OpenCV backend (fallback) ---

def try_opencv_backend(
    ip: str,
    port: int,
    requested_width: Optional[int],
    requested_height: Optional[int],
    target_fps: Optional[float],
) -> Optional[FrameSource]:
    try:
        return OpenCVGigEBackend(ip, port, requested_width, requested_height, target_fps)
    except Exception:
        return None


class OpenCVGigEBackend(FrameSource):
    """Fallback: cv2.VideoCapture with gige:// or IP URL."""

    def __init__(
        self,
        ip: str,
        port: int,
        requested_width: Optional[int],
        requested_height: Optional[int],
        target_fps: Optional[float],
    ) -> None:
        import cv2
        self._ip = ip
        self._port = port
        self._requested_width = requested_width
        self._requested_height = requested_height
        self._target_fps = target_fps
        self._cap = None
        self._error: Optional[str] = None

    def open(self) -> None:
        import cv2
        self._error = None
        self._cap = cv2.VideoCapture(f"gige://{self._ip}")
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(f"http://{self._ip}:{self._port}/video")
        if not self._cap.isOpened():
            self._error = "IP inacessível / cabo / subnet / firewall. Verifique a rede e a aba Diagnóstico."
            if self._cap:
                self._cap.release()
            self._cap = None

    def read_frame(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        import cv2
        if getattr(self, "_cap", None) is None or not self._cap.isOpened():
            return None, None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None, None
        return frame, time.monotonic()

    def close(self) -> None:
        if getattr(self, "_cap", None) is not None:
            self._cap.release()
            self._cap = None
        self._error = None

    def get_status(self) -> FrameSourceStatus:
        import cv2
        cap = getattr(self, "_cap", None)
        connected = cap is not None and cap.isOpened()
        return FrameSourceStatus(
            connected=connected,
            backend="OpenCV",
            error=getattr(self, "_error", None),
        )
