"""Unit tests for the SystemMode enum.

Each mode is a config dict describing which processes are enabled and the camera
resolution for that mode. These tests lock down the structural invariants so a
copy-paste slip when adding or editing a mode is caught in CI rather than at
runtime on the car.
"""

import pytest

from src.statemachine.systemMode import SystemMode

# Sub-systems that every mode toggles on/off.
PROCESS_KEYS = ["camera", "serial_handler", "semaphore", "traffic_com"]

ALL_MODES = list(SystemMode)


@pytest.mark.parametrize("mode", ALL_MODES)
def test_mode_has_all_process_sections(mode):
    config = mode.value
    for key in PROCESS_KEYS:
        assert key in config, f"{mode.name} is missing the '{key}' section"
        assert "process" in config[key], f"{mode.name}.{key} is missing 'process'"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_enabled_flag_is_bool(mode):
    """Every process's `enabled` flag must be a real bool — main.py branches on
    it directly, so a truthy string like "false" would silently start a
    process."""
    for key in PROCESS_KEYS:
        enabled = mode.value[key]["process"]["enabled"]
        assert isinstance(enabled, bool), f"{mode.name}.{key}.enabled is {type(enabled)}"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_mode_string_matches_enum_name(mode):
    """The `mode` field is the lowercase of the enum member name."""
    assert mode.value["mode"] == mode.name.lower()


@pytest.mark.parametrize("mode", ALL_MODES)
def test_camera_resolution_is_known(mode):
    """Camera resolution must be one the hardware layer understands."""
    valid = {"240p", "480p", "720p", "1080p"}
    resolution = mode.value["camera"]["thread"]["resolution"]
    assert resolution in valid, f"{mode.name} has unknown resolution {resolution!r}"


def test_expected_modes_exist():
    """Guard against an accidental rename/removal of a core mode."""
    names = {m.name for m in SystemMode}
    assert {"DEFAULT", "AUTO", "MANUAL", "LEGACY", "STOP"} <= names


def test_mode_names_are_unique():
    """Enum values are dicts (unhashable), so verify names don't collide."""
    names = [m.name for m in SystemMode]
    assert len(names) == len(set(names))
