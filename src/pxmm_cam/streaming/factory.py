"""Frame source factory: build USB or GigE source from config."""

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
    if streaming.source_type == "gige":
        from .gige_source import GigESource
        return GigESource(
            ip=streaming.gige_ip,
            port=streaming.gige_port,
            backend_preference=streaming.gige_backend,
            gentl_producer_path=streaming.gentl_producer_path or None,
            requested_width=streaming.requested_width,
            requested_height=streaming.requested_height,
            target_fps=streaming.target_fps,
        )
    raise ValueError(f"source_type não suportado: {streaming.source_type}")


# Alias for backward compatibility
SourceFactory = create_frame_source
