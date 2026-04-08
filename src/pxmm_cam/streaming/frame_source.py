"""FrameSource interface: open, read_frame, close, get_status."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass
class FrameSourceStatus:
    """Status report from a frame source."""

    connected: bool
    backend: str
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None
    fps: Optional[float] = None


class FrameSource(ABC):
    """Abstract base for USB and GigE frame sources. Frames are BGR (OpenCV convention)."""

    @abstractmethod
    def open(self) -> None:
        """Open the source. Idempotent; no-op if already open."""
        ...

    @abstractmethod
    def read_frame(self) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """Read one frame. Returns (frame_bgr, timestamp_sec) or (None, None) on failure/EOF."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the source and release resources."""
        ...

    @abstractmethod
    def get_status(self) -> FrameSourceStatus:
        """Return current status (backend, resolution, error)."""
        ...
