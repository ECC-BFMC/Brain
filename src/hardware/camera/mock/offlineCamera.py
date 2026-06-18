import base64

import cv2
import numpy as np


class OfflineCamera:
    """Deterministic offline camera frames for development mode."""

    def __init__(self):
        self._main_frames = []
        self._serial_frames = []
        self._frame_index = 0
        self._build_frames()

    def next_frame(self):
        index = self._frame_index
        self._frame_index = (index + 1) % len(self._main_frames)
        return self._main_frames[index], self._serial_frames[index]

    @property
    def frame_index(self):
        return self._frame_index

    @property
    def main_frame_count(self):
        return len(self._main_frames)

    @property
    def serial_frame_count(self):
        return len(self._serial_frames)

    def _build_frames(self):
        text = "OFFLINE"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 4.0
        thickness = 8
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)

        scale_s = 1.5
        thick_s = 3
        (tw2, th2), _ = cv2.getTextSize(text, font, scale_s, thick_s)

        pos_main_1 = (20, th + 20)
        pos_serial_1 = (10, th2 + 10)

        pos_main_2 = ((2048 - tw) // 2, (1080 + th) // 2)
        pos_serial_2 = ((512 - tw2) // 2, (270 + th2) // 2)

        pos_main_3 = (2048 - tw - 20, 1080 - 20)
        pos_serial_3 = (512 - tw2 - 10, 270 - 10)

        positions_main = [pos_main_1, pos_main_2, pos_main_3]
        positions_serial = [pos_serial_1, pos_serial_2, pos_serial_3]

        for p_main, p_serial in zip(positions_main, positions_serial):
            main_img = np.zeros((1080, 2048, 3), dtype=np.uint8)
            cv2.putText(main_img, text, p_main, font, scale, (255, 255, 255), thickness)
            _, main_enc = cv2.imencode(".jpg", main_img)
            self._main_frames.append(base64.b64encode(main_enc).decode("utf-8"))

            serial_img = np.zeros((270, 512, 3), dtype=np.uint8)
            cv2.putText(serial_img, text, p_serial, font, scale_s, (255, 255, 255), thick_s)
            _, serial_enc = cv2.imencode(".jpg", serial_img)
            self._serial_frames.append(base64.b64encode(serial_enc).decode("utf-8"))
