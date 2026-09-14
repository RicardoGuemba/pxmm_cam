"""GigE Vision source (Harvester/GStreamer/OpenCV). Não usado na produção Sentech; factory usa StapipySource."""

from typing import Optional, Tuple, Literal

import numpy as np

from .frame_source import FrameSource, FrameSourceStatus


class GigESource(FrameSource):
    """GigE frame source; delegates to Harvester, GStreamer, or OpenCV backend."""

    def __init__(
        self,
        ip: str,
        port: int = 3956,
        backend_preference: Literal["auto", "harvester", "gstreamer", "opencv"] = "auto",
        gentl_producer_path: Optional[str] = None,
        requested_width: Optional[int] = None,
        requested_height: Optional[int] = None,
        target_fps: Optional[float] = None,
    ) -> None:
        self._ip = ip.strip()
        self._port = port
        self._backend_preference = backend_preference
        self._gentl_producer_path = gentl_producer_path
        self._requested_width = requested_width
        self._requested_height = requested_height
        self._target_fps = target_fps
        self._backend: Optional[FrameSource] = None
        self._backend_name = ""

    def _resolve_backend(self) -> FrameSource:
        from .gige_backends import (
            try_harvester_backend,
            try_gstreamer_backend,
            try_opencv_backend,
            detect_gstreamer_available,
        )
        pref = self._backend_preference
        if pref == "harvester" or (pref == "auto" and self._gentl_producer_path):
            be = try_harvester_backend(
                self._ip, self._port,
                self._gentl_producer_path,
                self._requested_width, self._requested_height, self._target_fps,
            )
            if be is not None:
                return be
            if pref == "harvester":
                raise RuntimeError(
                    "GenTL Producer não configurado ou Harvester não conseguiu abrir a câmera. "
                    "Verifique gentl_producer_path no config e a aba Diagnóstico."
                )
        if pref == "gstreamer" or (pref == "auto" and detect_gstreamer_available()):
            be = try_gstreamer_backend(
                self._ip, self._port,
                self._requested_width, self._requested_height, self._target_fps,
            )
            if be is not None:
                return be
            if pref == "gstreamer":
                raise RuntimeError(
                    "Backend GStreamer indisponível ou falhou. "
                    "Verifique se o OpenCV foi compilado com GStreamer (aba Diagnóstico)."
                )
        be = try_opencv_backend(
            self._ip, self._port,
            self._requested_width, self._requested_height, self._target_fps,
        )
        if be is not None:
            return be
        raise RuntimeError(
            "Nenhum backend GigE disponível. Verifique: GenTL Producer (Harvester), "
            "OpenCV com GStreamer, ou drivers do fabricante. Use a aba Diagnóstico."
        )

    def open(self) -> None:
        if self._backend is not None:
            return
        self._backend = self._resolve_backend()
        self._backend.open()
        status = self._backend.get_status()
        self._backend_name = status.backend

    def read_frame(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        if self._backend is None:
            return None, None
        return self._backend.read_frame()

    def close(self) -> None:
        if self._backend is not None:
            self._backend.close()
            self._backend = None
        self._backend_name = ""

    def get_status(self) -> FrameSourceStatus:
        if self._backend is None:
            return FrameSourceStatus(
                connected=False,
                backend="GigE (não iniciado)",
                error="Chame open() primeiro.",
            )
        s = self._backend.get_status()
        s.backend = f"GigE via {self._backend_name}"
        return s
