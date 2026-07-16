"""Development simulator for the subset of :mod:`picamera2` used by Brain."""

import time

import cv2
import numpy as np


class Picamera2:
    """Small, deterministic stand-in with the application's Picamera2 API."""

    def __init__(self):
        self._configuration = None
        self._started = False
        self._controls = {}
        self._frames = {}
        self._frame_index = 0
        self._last_frame_time = None
        self._frame_interval = 1.0

    @staticmethod
    def global_camera_info():
        """Report one available simulated camera."""
        return [{"Id": "simulated-camera", "Model": "Brain Picamera2 Simulator"}]

    def create_preview_configuration(self, **kwargs):
        """Return a configuration object accepted by :meth:`configure`."""
        return kwargs

    def configure(self, configuration):
        self._configuration = configuration
        self._frames = {
            "main": self._build_frames(self._stream_size("main", (2048, 1080)), yuv=False),
            "lores": self._build_frames(self._stream_size("lores", (512, 270)), yuv=True),
        }
        self._frame_index = 0

    def start(self):
        if self._configuration is None:
            raise RuntimeError("Camera must be configured before it is started")
        self._started = True
        self._last_frame_time = time.monotonic()

    def stop(self):
        self._started = False

    def capture_array(self, name="main"):
        if not self._started:
            raise RuntimeError("Camera must be started before capturing frames")
        if name not in self._frames:
            raise KeyError(f"Unknown camera stream: {name}")

        self._update_frame_index()
        return self._frames[name][self._frame_index].copy()

    def set_controls(self, controls):
        self._controls.update(controls)

    @property
    def controls(self):
        """Expose applied controls for simulator diagnostics and tests."""
        return dict(self._controls)

    def _stream_size(self, name, default):
        stream = self._configuration.get(name, {})
        return tuple(stream.get("size", default))

    def _update_frame_index(self):
        now = time.monotonic()
        elapsed = now - self._last_frame_time
        if elapsed < 0:
            self._last_frame_time = now
            return
        if elapsed < self._frame_interval:
            return

        steps = int(elapsed / self._frame_interval)
        self._frame_index = (self._frame_index + steps) % len(self._frames["main"])
        self._last_frame_time += steps * self._frame_interval

    @staticmethod
    def _build_frames(size, yuv):
        width, height = size
        text = "OFFLINE"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(0.5, min(width / 512, height / 270) * 1.5)
        thickness = max(1, round(scale * 2))
        (text_width, text_height), _ = cv2.getTextSize(text, font, scale, thickness)
        margin = max(10, min(width, height) // 50)
        positions = [
            (margin, text_height + margin),
            ((width - text_width) // 2, (height + text_height) // 2),
            (width - text_width - margin, height - margin),
        ]

        frames = []
        for position in positions:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            cv2.putText(frame, text, position, font, scale, (255, 255, 255), thickness)
            if yuv:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
            frames.append(frame)
        return frames
