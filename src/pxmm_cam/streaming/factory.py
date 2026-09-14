"""Frame source factory: USB (OpenCV) ou Sentech StApi (stapipy)."""

from typing import TYPE_CHECKING

from .frame_source import FrameSource
from .usb_source import USBCameraSource

if TYPE_CHECKING:
    from pxmm_cam.config import AppConfig


def create_frame_source(config: "AppConfig") -> FrameSource:
    """Create a FrameSource from app config. OS can be used for path/backend quirks."""
    streaming = config.streaming
    if streaming.source_type == "usb":
        return USBCameraSource(
            camera_index=streaming.usb_camera_index,
            requested_width=streaming.requested_width,
            requested_height=streaming.requested_height,
            target_fps=streaming.target_fps,
        )
    if streaming.source_type == "stapipy":
        from .stapipy_source import StapipySource

        return StapipySource(
            device_index=streaming.device_index,
            fetch_timeout_ms=streaming.fetch_timeout_ms,
            target_fps=streaming.target_fps,
        )
    raise ValueError(f"source_type não suportado: {streaming.source_type}")


# Alias for backward compatibility
SourceFactory = create_frame_source
