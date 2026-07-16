import sys
import types

import cv2

import src.hardware.camera.threads.threadCamera as thread_camera_module
from sim import picamera2


def make_camera():
    camera = picamera2.Picamera2()
    configuration = camera.create_preview_configuration(
        buffer_count=1,
        queue=False,
        main={"format": "RGB888", "size": (2048, 1080)},
        lores={"size": (512, 270)},
        encode="lores",
    )
    camera.configure(configuration)
    camera.start()
    return camera


def test_dev_selection_ignores_an_installed_picamera2(monkeypatch):
    installed_picamera2 = types.ModuleType("picamera2")
    monkeypatch.setitem(sys.modules, "picamera2", installed_picamera2)

    selected_module = thread_camera_module._load_picamera2(use_simulator=True)
    assert selected_module is picamera2


def test_simulator_exposes_camera_and_expected_stream_shapes():
    assert picamera2.Picamera2.global_camera_info()
    camera = make_camera()

    main_frame = camera.capture_array("main")
    lores_yuv = camera.capture_array("lores")
    lores_frame = cv2.cvtColor(lores_yuv, cv2.COLOR_YUV2BGR_I420)

    assert main_frame.shape == (1080, 2048, 3)
    assert lores_frame.shape == (270, 512, 3)


def test_simulator_cycles_frames_using_elapsed_time(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(picamera2.time, "monotonic", lambda: now[0])
    camera = make_camera()
    first_frame = camera.capture_array("main")
    same_frame = camera.capture_array("main")

    now[0] += 1.0
    second_frame = camera.capture_array("main")

    now[0] += 1.0
    third_frame = camera.capture_array("main")

    now[0] += 1.0
    wrapped_frame = camera.capture_array("main")

    assert (first_frame == same_frame).all()
    assert not (first_frame == second_frame).all()
    assert not (second_frame == third_frame).all()
    assert (first_frame == wrapped_frame).all()


def test_simulator_applies_controls():
    camera = make_camera()
    camera.set_controls({"Brightness": 0.25, "Contrast": 4.0})

    assert camera.controls == {"Brightness": 0.25, "Contrast": 4.0}
