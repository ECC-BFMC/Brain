"""Unit tests for threadCamera recording.

Covers the lazy writer creation (sized from the actual frame, placed in the
recordings dir), the timed write cadence that keeps playback speed correct
regardless of the capture loop rate, and safe record-toggle handling.
cv2.VideoWriter is stubbed so no real video files are produced.
"""

from multiprocessing import Queue

import numpy as np
import pytest

import src.hardware.camera.threads.threadCamera as thread_camera_module
from src.hardware.camera.threads.threadCamera import threadCamera


class StubVideoWriter:
    def __init__(self, path, fourcc, fps, size):
        self.path = path
        self.fps = fps
        self.size = size
        self.frames = 0
        self.released = False

    def write(self, frame):
        self.frames += 1

    def release(self):
        self.released = True


def make_frame(height=1080, width=2048):
    return np.zeros((height, width, 3), dtype=np.uint8)


@pytest.fixture
def camera(monkeypatch, tmp_path):
    monkeypatch.setattr(thread_camera_module.cv2, "VideoWriter", StubVideoWriter)
    queues = {name: Queue() for name in ("Critical", "Warning", "General", "Config")}
    cam = threadCamera(queues, False, use_mock=True)
    cam.recordingsDir = str(tmp_path)
    yield cam
    cam.stop()


def test_writer_created_lazily_with_frame_size(camera):
    camera._handleRecordToggle(True)
    assert camera.video_writer is None  # nothing written yet

    camera._recordFrame(make_frame())
    writer = camera.video_writer
    assert writer is not None
    assert writer.size == (2048, 1080)
    assert writer.fps == camera.frame_rate
    assert writer.path.startswith(str(camera.recordingsDir))
    assert writer.frames == 1


def test_cadence_skips_frames_that_arrive_too_early(camera):
    camera._handleRecordToggle(True)
    camera._recordFrame(make_frame())
    # a frame arriving immediately after is ahead of the cadence -> dropped
    camera._recordFrame(make_frame())
    assert camera.video_writer.frames == 1


def test_cadence_writes_when_due(camera):
    camera._handleRecordToggle(True)
    camera._recordFrame(make_frame())
    camera._nextRecordFrameDue = 0.0  # simulate 1/frame_rate having elapsed
    camera._recordFrame(make_frame())
    assert camera.video_writer.frames == 2


def test_toggle_off_releases_writer(camera):
    camera._handleRecordToggle(True)
    camera._recordFrame(make_frame())
    writer = camera.video_writer

    camera._handleRecordToggle(False)
    assert writer.released
    assert camera.video_writer is None
    assert camera.recording is False


def test_toggle_off_without_recording_is_harmless(camera):
    camera._handleRecordToggle(False)
    assert camera.recording is False
    assert camera.video_writer is None


def test_double_toggle_on_keeps_single_writer(camera):
    camera._handleRecordToggle(True)
    camera._recordFrame(make_frame())
    writer = camera.video_writer

    camera._handleRecordToggle(True)
    assert camera.video_writer is writer
    assert not writer.released


def test_stop_releases_writer(camera):
    camera._handleRecordToggle(True)
    camera._recordFrame(make_frame())
    writer = camera.video_writer

    camera.stop()
    assert writer.released
    assert camera.video_writer is None
