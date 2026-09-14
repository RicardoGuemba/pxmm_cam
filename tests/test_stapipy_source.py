"""Contrato StApi (stapipy) no pxmm_cam — fakes, sem câmera nem wheel real."""

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pxmm_cam.config import AppConfig, StreamingConfig
from pxmm_cam.streaming.factory import create_frame_source
from pxmm_cam.streaming.stapipy_source import StapipySource
from pxmm_cam.streaming.usb_source import USBCameraSource


class _FakePixelInfo:
    def __init__(self, is_bayer=True, is_mono=False, bits=8):
        self.is_bayer = is_bayer
        self.is_mono = is_mono
        self.each_component_total_bit_count = bits

    def get_pixel_color_filter(self):
        return "BayerGR"


class _FakeImage:
    def __init__(self, width=8, height=8, pixel_format="BayerGR8"):
        self.width = width
        self.height = height
        self.pixel_format = pixel_format
        self._data = bytes(width * height)

    def get_image_data(self):
        return self._data


class _FakeBuffer:
    def __init__(self, image=None, timeout=False):
        self._image = image
        self._timeout = timeout
        self.info = SimpleNamespace(
            is_image_present=image is not None and not timeout,
            frame_id=1,
        )
        self.release_calls = 0

    def get_image(self):
        return self._image

    def release(self):
        self.release_calls += 1

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.release()
        return False


class _FakeDataStream:
    def __init__(self, buffers=None):
        self.start_calls = 0
        self.stop_calls = 0
        self.start_count_arg = None
        self.retrieve_calls = []
        self._buffers = list(buffers or [_FakeBuffer(_FakeImage())])

    def start_acquisition(self, count=None):
        self.start_calls += 1
        self.start_count_arg = count

    def stop_acquisition(self):
        self.stop_calls += 1

    def retrieve_buffer(self, timeout=5000, handling_timeout=None):
        self.retrieve_calls.append((timeout, handling_timeout))
        if handling_timeout is not None:
            raise RuntimeError("EStTimeoutHandling must not be passed")
        if self._buffers:
            return self._buffers.pop(0)
        return _FakeBuffer(timeout=True)


class _FakeDevice:
    def __init__(self, stream=None):
        self.stream = stream or _FakeDataStream()
        self.acquisition_start_calls = 0
        self.acquisition_stop_calls = 0
        self.info = SimpleNamespace(display_name="STC-MCA503POE-HS(fake)")

    def create_datastream(self):
        return self.stream

    def acquisition_start(self):
        self.acquisition_start_calls += 1

    def acquisition_stop(self):
        self.acquisition_stop_calls += 1


class _FakeSystem:
    def __init__(self, device=None):
        self.device = device or _FakeDevice()
        self.create_first_device_calls = 0

    def create_first_device(self, access_flags=None):
        self.create_first_device_calls += 1
        return self.device


class _FakeStApi:
    def __init__(self, system=None, raise_on_init=None):
        self.system = system or _FakeSystem()
        self.initialize_calls = 0
        self.terminate_calls = 0
        self.raise_on_init = raise_on_init
        self.PyStError = RuntimeError
        self.EStTimeoutHandling = SimpleNamespace(Return="Return")

    def initialize(self):
        self.initialize_calls += 1
        if self.raise_on_init is not None:
            raise self.raise_on_init

    def terminate(self):
        self.terminate_calls += 1

    def create_system(self):
        return self.system

    def get_pixel_format_info(self, pixel_format):
        return _FakePixelInfo(is_bayer="Bayer" in str(pixel_format))


def _stapipy_config(**kwargs) -> AppConfig:
    data = {"source_type": "stapipy", "device_index": 0, "fetch_timeout_ms": 400}
    data.update(kwargs)
    return AppConfig(streaming=StreamingConfig(**data))


class TestStapipyFactory:
    def test_create_stapipy_source(self):
        src = create_frame_source(_stapipy_config())
        assert isinstance(src, StapipySource)

    def test_gige_alias_becomes_stapipy(self):
        cfg = AppConfig(streaming=StreamingConfig(source_type="gige"))
        assert cfg.streaming.source_type == "stapipy"
        src = create_frame_source(cfg)
        assert isinstance(src, StapipySource)

    def test_usb_factory_unchanged(self):
        cfg = AppConfig(streaming=StreamingConfig(source_type="usb", usb_camera_index=1))
        src = create_frame_source(cfg)
        assert isinstance(src, USBCameraSource)


class TestStapipyLifecycle:
    def test_open_follows_stapi_order(self):
        stapi = _FakeStApi()
        src = StapipySource(st_module=stapi, device_index=0)
        src.open()
        assert stapi.initialize_calls == 1
        assert stapi.system.create_first_device_calls == 1
        assert stapi.system.device.stream.start_calls == 1
        assert stapi.system.device.acquisition_start_calls == 1
        assert stapi.system.device.stream.start_count_arg is None
        assert src.get_status().connected is True
        assert src.get_status().backend == "StApi (stapipy)"

    def test_read_frame_retrieve_buffer_one_arg_bgr_copy(self):
        stapi = _FakeStApi()
        src = StapipySource(st_module=stapi, fetch_timeout_ms=400)
        src.open()
        frame, ts = src.read_frame()
        calls = stapi.system.device.stream.retrieve_calls
        assert len(calls) == 1
        timeout, handling = calls[0]
        assert timeout == 400
        assert handling is None
        assert frame is not None
        assert ts is not None
        assert frame.ndim == 3
        assert frame.shape[2] == 3
        assert frame.dtype == np.uint8
        assert bool(frame.flags["OWNDATA"])
        assert frame.shape[0] == 8 and frame.shape[1] == 8

    def test_retrieve_timeout_returns_none(self):
        stream = _FakeDataStream(buffers=[_FakeBuffer(timeout=True)])
        stapi = _FakeStApi(_FakeSystem(_FakeDevice(stream)))
        src = StapipySource(st_module=stapi)
        src.open()
        frame, ts = src.read_frame()
        assert frame is None
        assert ts is None

    def test_close_same_thread_stops_and_terminates(self):
        stapi = _FakeStApi()
        src = StapipySource(st_module=stapi)
        src.open()
        src.close()
        device = stapi.system.device
        assert device.acquisition_stop_calls == 1
        assert device.stream.stop_calls == 1
        assert stapi.terminate_calls == 1
        assert src.get_status().connected is False

    def test_close_wrong_thread_does_not_terminate(self):
        stapi = _FakeStApi()
        src = StapipySource(st_module=stapi)
        src.open()
        errors = []

        def _close_other():
            src.close()
            errors.append(stapi.terminate_calls)

        t = threading.Thread(target=_close_other)
        t.start()
        t.join()
        assert errors == [0]
        assert src.get_status().connected is True
        src.close()
        assert stapi.terminate_calls == 1

    def test_interrupt_acquisition_is_noop(self):
        stapi = _FakeStApi()
        src = StapipySource(st_module=stapi)
        src.open()
        src.interrupt_acquisition()
        assert stapi.system.device.acquisition_stop_calls == 0
        assert stapi.terminate_calls == 0
        src.close()

    def test_reopen_after_close_initializes_again(self):
        stapi = _FakeStApi()
        src = StapipySource(st_module=stapi)
        src.open()
        src.close()
        src.open()
        assert stapi.initialize_calls == 2
        assert stapi.terminate_calls == 1

    def test_open_busy_releases_and_raises(self):
        stapi = _FakeStApi(raise_on_init=RuntimeError("PyStError: busy"))
        src = StapipySource(st_module=stapi)
        with pytest.raises(RuntimeError):
            src.open()
        assert src.get_status().connected is False
        assert src.get_status().error
        assert "StApi" in src.get_status().error or "busy" in src.get_status().error.lower()

    def test_missing_stapipy_raises_clear_error(self, monkeypatch):
        import builtins

        orig = builtins.__import__

        def _imp(name, *args, **kwargs):
            if name == "stapipy" or str(name).startswith("stapipy"):
                raise ImportError("missing")
            return orig(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _imp)
        src = StapipySource()
        with pytest.raises(RuntimeError, match="stapipy"):
            src.open()
        assert src.get_status().connected is False
        assert src.get_status().error
        assert "stapipy" in src.get_status().error.lower()
