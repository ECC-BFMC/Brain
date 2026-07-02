"""Unit tests for the NUCLEO serial command encoder.

MessageConverter turns high-level actions ("speed", "steer", ...) into the exact
`#action:v1;v2;;\\r\\n` frames the Nucleo expects, and rejects malformed ones.
It is pure logic and is the contract for everything the car sends over serial.
"""

from src.hardware.serialhandler.threads.messageconverter import MessageConverter


# --------------------------------------------------------------------------- #
# get_command — framing
# --------------------------------------------------------------------------- #
def test_single_arg_command_framing():
    assert MessageConverter().get_command("speed", speed=100) == "#speed:100;;\r\n"


def test_multi_arg_command_keeps_declared_order():
    # vcd args are declared [speed, steer, time]; kwargs order must not matter.
    cmd = MessageConverter().get_command("vcd", time=5, speed=100, steer=20)
    assert cmd == "#vcd:100;20;5;;\r\n"


def test_negative_value_is_allowed_within_digit_budget():
    assert MessageConverter().get_command("steer", steerAngle=-120) == "#steer:-120;;\r\n"


# --------------------------------------------------------------------------- #
# verify_command — rejection paths (get_command returns "error")
# --------------------------------------------------------------------------- #
def test_wrong_argument_count_is_rejected():
    assert MessageConverter().get_command("speed", speed=1, extra=2) == "error"


def test_unknown_kwarg_name_is_rejected():
    assert MessageConverter().get_command("speed", steerAngle=1) == "error"


def test_non_int_value_is_rejected():
    assert MessageConverter().get_command("speed", speed=1.5) == "error"


def test_too_many_digits_is_rejected():
    # speed budget is 3 digits; 12345 overflows it.
    assert MessageConverter().get_command("speed", speed=12345) == "error"


def test_negative_over_digit_budget_is_rejected():
    # kl budget is 2 digits; -100 is 3 significant digits -> rejected.
    assert MessageConverter().get_command("kl", mode=-100) == "error"


def test_verify_command_accepts_valid_and_rejects_invalid():
    mc = MessageConverter()
    assert mc.verify_command("battery", {"activate": 1}) is True
    assert mc.verify_command("battery", {"activate": 1, "extra": 0}) is False
