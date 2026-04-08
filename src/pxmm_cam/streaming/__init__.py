"""Streaming: FrameSource abstraction and USB/GigE backends."""

from .frame_source import FrameSource, FrameSourceStatus
from .usb_source import (
    USBCameraSource,
    detect_usb_camera_indices,
    first_external_usb_index,
)
from .factory import create_frame_source, SourceFactory
from .capture_worker import CaptureWorker

__all__ = [
    "FrameSource",
    "FrameSourceStatus",
    "USBCameraSource",
    "detect_usb_camera_indices",
    "first_external_usb_index",
    "create_frame_source",
    "SourceFactory",
    "CaptureWorker",
]
