"""Fonte Omron Sentech via StApi Python (stapipy). Sem Harvester/CTI/OpenCV GigE.

Ciclo validado (igual ao adapter de referência):
initialize → create_system → create_first_device → create_datastream →
start_acquisition → acquisition_start. retrieve_buffer só com timeout_ms.
Pixels copiados antes de sair do retrieve. close no mesmo thread:
acquisition_stop → stop_acquisition → stapipy.terminate.

Não redimensiona o frame (medição px/mm precisa da resolução nativa).
requested_width/requested_height são ignorados de propósito.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional, Tuple

import cv2
import numpy as np

from .frame_source import FrameSource, FrameSourceStatus

logger = logging.getLogger(__name__)

_BAYER_TO_BGR = {
    "bayerRG": cv2.COLOR_BAYER_RG2BGR,
    "bayerGR": cv2.COLOR_BAYER_GR2BGR,
    "bayerGB": cv2.COLOR_BAYER_GB2BGR,
    "bayerBG": cv2.COLOR_BAYER_BG2BGR,
    "BayerRG": cv2.COLOR_BAYER_RG2BGR,
    "BayerGR": cv2.COLOR_BAYER_GR2BGR,
    "BayerGB": cv2.COLOR_BAYER_GB2BGR,
    "BayerBG": cv2.COLOR_BAYER_BG2BGR,
}

_STAPIPY_IMPORT_MSG = (
    "Biblioteca stapipy não instalada. Instale o wheel Omron após o "
    "SentechSDK (não está no PyPI). SDK típico em /opt/sentech."
)

_STAPIPY_OPEN_MSG = (
    "Não foi possível abrir a câmera Omron Sentech (StApi). "
    "Verifique SDK, variáveis .stprofile e se outro cliente "
    "(StViewer) ainda segura o device."
)


class StapipySource(FrameSource):
    """Produção Sentech: StApi no thread do CaptureWorker."""

    def __init__(
        self,
        device_index: int = 0,
        fetch_timeout_ms: int = 400,
        target_fps: Optional[float] = None,
        st_module: Any = None,
    ) -> None:
        self.device_index = int(device_index)
        self.fetch_timeout_ms = int(fetch_timeout_ms)
        self._fps = float(target_fps) if target_fps else None
        self._st = st_module
        self._system = None
        self._device = None
        self._datastream = None
        self._initialized = False
        self._is_open = False
        self._owner_thread_ident: Optional[int] = None
        self._width = 0
        self._height = 0
        self._first_frame_logged = False
        self._error: Optional[str] = None

    def _stapi(self) -> Any:
        if self._st is not None:
            return self._st
        try:
            import stapipy as st  # type: ignore
        except ImportError as e:
            raise RuntimeError(_STAPIPY_IMPORT_MSG) from e
        self._st = st
        return st

    def open(self) -> None:
        if self._is_open:
            return
        self._error = None
        try:
            st = self._stapi()
            st.initialize()
            self._initialized = True
            self._system = st.create_system()
            if self.device_index <= 0:
                self._device = self._system.create_first_device()
            else:
                iface = None
                get_iface = getattr(self._system, "create_first_interface", None)
                if callable(get_iface):
                    iface = get_iface()
                if iface is None or not hasattr(iface, "create_device_by_index"):
                    raise RuntimeError(
                        f"Índice de câmera {self.device_index} pedido, mas a API StApi "
                        "não expôs create_device_by_index. Use índice 0 ou atualize o SDK."
                    )
                self._device = iface.create_device_by_index(self.device_index)
            self._datastream = self._device.create_datastream()
            self._datastream.start_acquisition()
            self._device.acquisition_start()
            self._owner_thread_ident = threading.get_ident()
            self._is_open = True
            self._first_frame_logged = False
            display = None
            info = getattr(self._device, "info", None)
            if info is not None:
                display = getattr(info, "display_name", None)
            logger.info(
                "stapipy_opened device_index=%s display_name=%s",
                self.device_index,
                display,
            )
        except RuntimeError as e:
            msg = str(e)
            if "stapipy não instalada" in msg or "create_device_by_index" in msg:
                self._error = msg
                self._teardown()
                raise
            self._error = _STAPIPY_OPEN_MSG
            self._teardown()
            raise RuntimeError(_STAPIPY_OPEN_MSG) from e
        except Exception as e:
            self._error = _STAPIPY_OPEN_MSG
            self._teardown()
            raise RuntimeError(_STAPIPY_OPEN_MSG) from e

    def read_frame(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        if not self._is_open or self._datastream is None:
            return None, None
        timeout_ms = max(1, int(self.fetch_timeout_ms))
        try:
            # Sample Omron: retrieve_buffer() sem EStTimeoutHandling. O 2.º argumento
            # inválido aborta em GenICam C++ (LogicalErrorException / std::terminate).
            retrieved = self._datastream.retrieve_buffer(timeout_ms)
            if retrieved is None:
                return None, None
            if hasattr(retrieved, "__enter__"):
                with retrieved as buffer:
                    image = self._decode_buffer(buffer)
            else:
                image = self._decode_buffer(retrieved)
                release = getattr(retrieved, "release", None)
                if callable(release):
                    try:
                        release()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("stapipy_read_failed: %s", e or type(e).__name__)
            return None, None
        if image is None:
            return None, None
        return image, time.monotonic()

    def _decode_buffer(self, buffer: Any) -> Optional[np.ndarray]:
        info = getattr(buffer, "info", None)
        if info is not None and not getattr(info, "is_image_present", True):
            return None
        get_image = getattr(buffer, "get_image", None)
        if not callable(get_image):
            return None
        st_image = get_image()
        if st_image is None:
            return None
        return self._image_to_bgr(st_image)

    def _image_to_bgr(self, st_image: Any) -> Optional[np.ndarray]:
        """Copia pixels antes de sair do retrieve. UI/medição usam BGR nativo."""
        data = st_image.get_image_data()
        width = int(st_image.width)
        height = int(st_image.height)
        pixel_format = getattr(st_image, "pixel_format", "")
        st = self._st
        info = None
        if st is not None and hasattr(st, "get_pixel_format_info"):
            try:
                info = st.get_pixel_format_info(pixel_format)
            except Exception:
                info = None
        bits = 8
        is_bayer = "bayer" in str(pixel_format).lower()
        is_mono = "mono" in str(pixel_format).lower()
        if info is not None:
            bits = int(getattr(info, "each_component_total_bit_count", 8) or 8)
            is_bayer = bool(getattr(info, "is_bayer", is_bayer))
            is_mono = bool(getattr(info, "is_mono", is_mono))
        if bits > 8:
            nparr = np.frombuffer(data, np.uint16).copy()
            valid = (
                int(getattr(info, "each_component_valid_bit_count", bits) or bits)
                if info
                else bits
            )
            division = pow(2, max(0, valid - 8))
            nparr = (nparr / division).astype(np.uint8) if division else nparr.astype(np.uint8)
        else:
            nparr = np.frombuffer(data, np.uint8).copy()
        nparr = nparr.reshape(height, width, 1)
        if is_bayer:
            code = self._bayer_code(st, info, pixel_format)
            nparr = cv2.cvtColor(nparr, code)
        elif is_mono or nparr.ndim == 2 or nparr.shape[2] == 1:
            nparr = cv2.cvtColor(nparr, cv2.COLOR_GRAY2BGR)
        return self._finish_frame(nparr, width, height)

    def _bayer_code(self, st: Any, info: Any, pixel_format: Any) -> int:
        filt = None
        if info is not None and hasattr(info, "get_pixel_color_filter"):
            try:
                filt = info.get_pixel_color_filter()
            except Exception:
                filt = None
        enum = getattr(st, "EStPixelColorFilter", None) if st is not None else None
        if filt is not None and enum is not None:
            mapping = (
                (getattr(enum, "BayerRG", None), cv2.COLOR_BAYER_RG2BGR),
                (getattr(enum, "BayerGR", None), cv2.COLOR_BAYER_GR2BGR),
                (getattr(enum, "BayerGB", None), cv2.COLOR_BAYER_GB2BGR),
                (getattr(enum, "BayerBG", None), cv2.COLOR_BAYER_BG2BGR),
            )
            for key, code in mapping:
                if key is not None and filt == key:
                    return code
        bayer_key = str(filt or pixel_format)
        for key, cvt in _BAYER_TO_BGR.items():
            if key.lower() in bayer_key.lower():
                return cvt
        return cv2.COLOR_BAYER_GR2BGR

    def _finish_frame(self, nparr: np.ndarray, native_w: int, native_h: int) -> np.ndarray:
        if not self._first_frame_logged:
            self._width = nparr.shape[1]
            self._height = nparr.shape[0]
            logger.info(
                "stapipy_first_frame native=(%s, %s) output=(%s, %s)",
                native_w,
                native_h,
                self._width,
                self._height,
            )
            self._first_frame_logged = True
        return np.ascontiguousarray(nparr).copy()

    def close(self) -> None:
        if not self._is_open and not self._initialized:
            return
        owner = self._owner_thread_ident
        if owner is not None and threading.get_ident() != owner:
            logger.error(
                "stapipy_close_wrong_thread owner_ident=%s caller_ident=%s",
                owner,
                threading.get_ident(),
            )
            return
        self._is_open = False
        self._teardown()
        self._owner_thread_ident = None
        logger.info("source_closed backend=stapipy")

    def interrupt_acquisition(self) -> None:
        """No-op: acquisition_stop na UI aborta o GenICam. O worker faz close()."""
        return

    def _teardown(self) -> None:
        try:
            if self._device is not None:
                try:
                    self._device.acquisition_stop()
                except Exception:
                    pass
        finally:
            try:
                if self._datastream is not None:
                    self._datastream.stop_acquisition()
            except Exception:
                pass
            self._datastream = None
            self._device = None
            self._system = None
            if self._initialized:
                try:
                    if self._st is not None:
                        self._st.terminate()
                except Exception:
                    pass
                self._initialized = False
            self._is_open = False

    def get_status(self) -> FrameSourceStatus:
        return FrameSourceStatus(
            connected=self._is_open,
            backend="StApi (stapipy)",
            width=self._width or None,
            height=self._height or None,
            error=self._error,
            fps=self._fps,
        )
