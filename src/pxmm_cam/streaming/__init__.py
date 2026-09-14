"""Streaming: FrameSource abstraction, USB and StApi (stapipy) backends."""

from .frame_source import FrameSource, FrameSourceStatus
from .usb_source import (
    USBCameraSource,
    detect_usb_camera_indices,
    first_external_usb_index,
)
from .factory import create_frame_source, SourceFactory
from .capture_worker import CaptureWorker
from .stapipy_source import StapipySource

__all__ = [
    "FrameSource",
    "FrameSourceStatus",
    "USBCameraSource",
    "StapipySource",
    "detect_usb_camera_indices",
    "first_external_usb_index",
    "create_frame_source",
    "SourceFactory",
    "CaptureWorker",
]
