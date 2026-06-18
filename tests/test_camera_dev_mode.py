import contextlib
import io
import unittest
from unittest.mock import patch

from src.hardware.camera.threads.threadCamera import threadCamera


class CameraDevModeTests(unittest.TestCase):
    def make_thread_shell(self, dev_mode):
        camera_thread = threadCamera.__new__(threadCamera)
        camera_thread.dev_mode = dev_mode
        return camera_thread

    def test_no_picamera_disables_camera_without_dev_mode(self):
        camera_thread = self.make_thread_shell(dev_mode=False)

        with patch("src.hardware.camera.threads.threadCamera.HAS_PICAMERA2", False):
            with contextlib.redirect_stdout(io.StringIO()):
                camera_thread._init_camera()

        self.assertIsNone(camera_thread.camera)
        self.assertFalse(hasattr(camera_thread, "offlineCamera"))

    def test_no_picamera_uses_offline_frames_in_dev_mode(self):
        camera_thread = self.make_thread_shell(dev_mode=True)

        with patch("src.hardware.camera.threads.threadCamera.HAS_PICAMERA2", False):
            with contextlib.redirect_stdout(io.StringIO()):
                camera_thread._init_camera()

        self.assertIsNone(camera_thread.camera)
        self.assertEqual(0, camera_thread.offlineCamera.frame_index)
        self.assertEqual(3, camera_thread.offlineCamera.main_frame_count)
        self.assertEqual(3, camera_thread.offlineCamera.serial_frame_count)

    def test_dev_mode_uses_offline_frames_without_checking_hardware(self):
        camera_thread = self.make_thread_shell(dev_mode=True)

        with patch("src.hardware.camera.threads.threadCamera.HAS_PICAMERA2", True):
            with patch("src.hardware.camera.threads.threadCamera.picamera2", create=True) as picamera2_mock:
                picamera2_mock.Picamera2.global_camera_info.side_effect = AssertionError(
                    "Dev mode must not inspect camera hardware"
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    camera_thread._init_camera()

        self.assertIsNone(camera_thread.camera)
        self.assertEqual(3, camera_thread.offlineCamera.main_frame_count)


if __name__ == "__main__":
    unittest.main()
