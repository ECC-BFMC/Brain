"""Unit tests for the state-machine transition table.

The transition table is the safety-critical core of mode switching: it decides
which mode the car may move to when a dashboard button is pressed. It is pure
lookup logic with no hardware or multiprocessing dependency, so it is fully
exercised here.
"""

import itertools

import pytest

from src.statemachine.systemMode import SystemMode
from src.statemachine.transitionTable import TransitionTable

# The four dashboard buttons that drive every transition.
BUTTONS = [
    "dashboard_auto_button",
    "dashboard_manual_button",
    "dashboard_legacy_button",
    "dashboard_stop_button",
]

# Which mode each button leads to, regardless of the current mode.
BUTTON_TARGET = {
    "dashboard_auto_button": SystemMode.AUTO,
    "dashboard_manual_button": SystemMode.MANUAL,
    "dashboard_legacy_button": SystemMode.LEGACY,
    "dashboard_stop_button": SystemMode.STOP,
}

ALL_MODES = list(SystemMode)


@pytest.mark.parametrize("mode,button", itertools.product(ALL_MODES, BUTTONS))
def test_every_button_is_valid_from_every_mode(mode, button):
    """Each of the four buttons is accepted from every mode and lands on the
    mode that button represents."""
    result = TransitionTable.get_next_mode(mode, button)

    assert result["transition_valid"] is True
    assert result["next_mode"] is BUTTON_TARGET[button]


@pytest.mark.parametrize("mode", ALL_MODES)
def test_unknown_action_is_rejected(mode):
    """An action that isn't a known button is rejected without raising."""
    result = TransitionTable.get_next_mode(mode, "not_a_real_button")

    assert result["transition_valid"] is False
    assert result["next_mode"] is None


@pytest.mark.parametrize("mode", ALL_MODES)
def test_empty_action_is_rejected(mode):
    result = TransitionTable.get_next_mode(mode, "")

    assert result["transition_valid"] is False
    assert result["next_mode"] is None


def test_unknown_current_mode_is_rejected():
    """A current mode that isn't in the table returns an invalid transition
    instead of raising a KeyError."""
    result = TransitionTable.get_next_mode("garbage_mode", "dashboard_auto_button")

    assert result["transition_valid"] is False
    assert result["next_mode"] is None


@pytest.mark.parametrize("mode", [SystemMode.AUTO, SystemMode.MANUAL, SystemMode.LEGACY, SystemMode.STOP])
def test_self_transition_is_allowed(mode):
    """AUTO/MANUAL/LEGACY/STOP each keep their own button available as a
    self-transition (documented special case in the table)."""
    button = {
        SystemMode.AUTO: "dashboard_auto_button",
        SystemMode.MANUAL: "dashboard_manual_button",
        SystemMode.LEGACY: "dashboard_legacy_button",
        SystemMode.STOP: "dashboard_stop_button",
    }[mode]

    result = TransitionTable.get_next_mode(mode, button)

    assert result["transition_valid"] is True
    assert result["next_mode"] is mode


def test_default_mode_has_no_self_transition():
    """DEFAULT is the boot mode; there is no button that returns to it."""
    for button in BUTTONS:
        result = TransitionTable.get_next_mode(SystemMode.DEFAULT, button)
        assert result["next_mode"] is not SystemMode.DEFAULT
