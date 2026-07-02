"""Unit tests for the pure logic in the calibration component.

Calibration turns measured wheel positions into a steering angle + speed and
persists calibration runs to disk. The geometry (`calculate_actual_steer_speed`)
and the measurement save/load/validate paths are pure and are tested here with
mocked queues/socketio. The scipy-backed spline fitting and the Nucleo I/O are
out of scope.

Requires scipy (declared in requirements.txt); skipped if it isn't installed.
"""

import json

import pytest

pytest.importorskip("scipy")  # calibration.py imports scipy at module load.

from unittest.mock import MagicMock  # noqa: E402

from src.dashboard.components.calibration import Calibration  # noqa: E402


@pytest.fixture
def calib():
    queues = {name: MagicMock() for name in ("Critical", "Warning", "General", "Config", "Log")}
    return Calibration(queues, MagicMock())


# --------------------------------------------------------------------------- #
# calculate_actual_steer_speed  (pure geometry)
# --------------------------------------------------------------------------- #
def test_straight_line_gives_zero_steer(calib):
    # Equal front/back x and a centred back-right -> the car went straight.
    steer, speed = calib.calculate_actual_steer_speed(100, 0, 0, 10)
    assert steer == 0
    # 100 mm over dt=10 deciseconds (=1 s) -> 100 mm/s.
    assert speed == pytest.approx(100.0)


def test_zero_dt_yields_zero_speed(calib):
    steer, speed = calib.calculate_actual_steer_speed(100, 0, 0, 0)
    assert steer == 0
    assert speed == 0


def test_turning_produces_positive_angle_and_finite_speed(calib):
    import math

    steer, speed = calib.calculate_actual_steer_speed(100, 20, 60, 10)
    assert steer > 0
    assert math.isfinite(speed)


def test_out_of_range_geometry_is_clamped_not_crashed(calib):
    # x_front_right far larger than the wheelbase would drive H_vec_x > 1 and
    # blow up sqrt(1 - x^2); the code clamps instead of raising.
    steer, speed = calib.calculate_actual_steer_speed(100, 0, 10000, 10)
    import math
    assert math.isfinite(steer)


# --------------------------------------------------------------------------- #
# _normalize_measurement_id
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,expected", [
    ("  My Run!! ", "my_run"),
    ("left-right_1", "left-right_1"),
    ("***", "calibration"),
    ("", "calibration"),
])
def test_normalize_measurement_id(calib, raw, expected):
    assert calib._normalize_measurement_id(raw) == expected


# --------------------------------------------------------------------------- #
# collect_calibration_points
# --------------------------------------------------------------------------- #
def test_collect_points_empty_when_no_measurements(calib):
    # Fresh template has all actual* values as None -> nothing collected.
    assert calib.collect_calibration_points("Steer") == []
    assert calib.collect_calibration_points("Speed") == []


# --------------------------------------------------------------------------- #
# save / load / validate roundtrip
# --------------------------------------------------------------------------- #
@pytest.fixture
def calib_with_tmpdir(calib, tmp_path, monkeypatch):
    monkeypatch.setattr(calib, "_get_saved_measurements_dir", lambda: str(tmp_path))
    return calib, tmp_path


def test_save_requires_a_name(calib_with_tmpdir):
    calib, _ = calib_with_tmpdir
    with pytest.raises(ValueError):
        calib.save_measurements("   ")


def test_save_then_load_roundtrip(calib_with_tmpdir):
    calib, tmp_path = calib_with_tmpdir

    # Give the run some completion state so the roundtrip is observable.
    calib.left_completed = True
    calib.steering_offset = 1.5

    result = calib.save_measurements("My Calibration")
    saved_id = result["measurement"]["id"]
    assert (tmp_path / f"{saved_id}.json").exists()

    # Reset state, then load the file back and confirm it is restored.
    calib.left_completed = False
    calib.steering_offset = 0
    loaded = calib.load_measurements(saved_id)
    assert loaded["measurement"]["id"] == saved_id
    assert loaded["calibration"]["left"] is True
    assert calib.steering_offset == pytest.approx(1.5)


def test_load_missing_measurement_raises(calib_with_tmpdir):
    calib, _ = calib_with_tmpdir
    with pytest.raises(FileNotFoundError):
        calib.load_measurements("does-not-exist")


def test_validate_rejects_non_dict_payload(calib):
    with pytest.raises(ValueError):
        calib._validate_saved_measurement(["not", "a", "dict"])


def test_validate_rejects_wrong_calibration_mode(calib):
    with pytest.raises(ValueError):
        calib._validate_saved_measurement({"calibrationMode": "advanced"})


def test_validate_rejects_missing_commands(calib):
    with pytest.raises(ValueError):
        calib._validate_saved_measurement({"calibrationMode": "basic"})


def test_saved_file_is_valid_json(calib_with_tmpdir):
    calib, tmp_path = calib_with_tmpdir
    result = calib.save_measurements("roundtrip")
    saved_id = result["measurement"]["id"]
    with open(tmp_path / f"{saved_id}.json", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["name"] == "roundtrip"
    assert payload["calibrationMode"] == "basic"
