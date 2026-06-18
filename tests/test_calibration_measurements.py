import copy
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

scipy_module = types.ModuleType("scipy")
scipy_interpolate_module = types.ModuleType("scipy.interpolate")
scipy_interpolate_module.CubicSpline = object
scipy_module.interpolate = scipy_interpolate_module
sys.modules.setdefault("scipy", scipy_module)
sys.modules.setdefault("scipy.interpolate", scipy_interpolate_module)

from src.dashboard.components.calibration import Calibration


class CalibrationMeasurementPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.calibration = Calibration.__new__(Calibration)
        self.calibration.commands_template = {
            "left": [{} for _ in range(7)],
            "right": [{} for _ in range(7)],
            "backward": [{} for _ in range(5)],
        }
        self.calibration.commands = copy.deepcopy(self.calibration.commands_template)
        self.calibration.test_run = {"speed": 350, "steer": 0, "time": 30}
        self.calibration.left_completed = False
        self.calibration.right_completed = False
        self.calibration.backward_completed = False
        self.calibration.test_run_completed = False
        self.calibration.max_angle_left = None
        self.calibration.max_angle_right = None
        self.calibration.steering_offset = 0
        self.calibration.zero_offset_spline_data_for_frontend = None
        self.calibration.current_step = 0
        self.calibration.current_command = None
        self.calibration.valid_angles = []

    def test_loads_existing_basic_measurement(self):
        measurement_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "calibration",
            "measurements",
            "test.json",
        )
        with open(measurement_path, "r", encoding="utf-8") as measurement_file:
            payload = json.load(measurement_file)

        self.calibration._apply_loaded_measurements(payload)

        self.assertTrue(self.calibration.left_completed)
        self.assertTrue(self.calibration.right_completed)
        self.assertTrue(self.calibration.backward_completed)
        self.assertTrue(self.calibration.test_run_completed)
        self.assertEqual(0.35, self.calibration.steering_offset)
        self.assertEqual(7, len(self.calibration.commands["left"]))
        self.assertEqual(5, len(self.calibration.commands["backward"]))

    def test_rejects_unsupported_measurement_mode(self):
        payload = {
            "calibrationMode": "basic",
            "measurementMode": "imu_encoder",
            "commands": {},
        }

        with self.assertRaisesRegex(ValueError, "manual measurements only"):
            self.calibration._validate_saved_measurement(payload)

    def test_save_and_load_round_trip(self):
        measurement_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "calibration",
            "measurements",
            "test.json",
        )
        with open(measurement_path, "r", encoding="utf-8") as measurement_file:
            payload = json.load(measurement_file)
        self.calibration._apply_loaded_measurements(payload)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(
                self.calibration,
                "_get_saved_measurements_dir",
                return_value=temp_dir,
            ):
                saved = self.calibration.save_measurements("Round Trip")
                loaded = self.calibration.load_measurements("round_trip")

        self.assertEqual("round_trip", saved["measurement"]["id"])
        self.assertEqual("Round Trip", loaded["measurement"]["name"])
        self.assertTrue(loaded["calibration"]["left"])
        self.assertEqual(0.35, loaded["calibration"]["steeringOffset"])


if __name__ == "__main__":
    unittest.main()
