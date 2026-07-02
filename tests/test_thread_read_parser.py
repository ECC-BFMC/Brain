"""Unit tests for the NUCLEO -> RPi message parser (threadRead.send_queue).

send_queue decodes framed `@action:value` telemetry from the Nucleo and routes
it to the right message sender. The routing + value math (battery %, imu
data/ack split, vcdCalib run-done vs PWM) are the logic under test. threadRead's
constructor starts a repeating heartbeat Timer, so it is neutralised here; the
senders are replaced with mocks to observe what would be published.
"""

from unittest.mock import MagicMock

import pytest

import src.hardware.serialhandler.threads.threadRead as threadRead_mod
from src.hardware.serialhandler.threads.threadRead import threadRead


class _Queues(dict):
    """Auto-vivifying queue dict so the real senders can be constructed."""

    class _Q:
        def put(self, *args, **kwargs):
            pass

    def __missing__(self, key):
        q = self._Q()
        self[key] = q
        return q


@pytest.fixture
def reader(monkeypatch):
    # Stop __init__ from scheduling the recurring heartbeat Timer.
    monkeypatch.setattr(threadRead_mod.threadRead, "queue_sending", lambda self: None)
    tr = threadRead(process=MagicMock(), queueList=_Queues(), debugger=False)
    # Swap the senders we assert on for mocks.
    for name in ("currentSpeedSender", "currentSteerSender", "batteryLvlSender",
                 "instantConsumptionSender", "imuDataSender", "imuAckSender",
                 "calibRunDoneSender", "calibPWMDataSender", "steeringLimitsSender",
                 "aliveSignalSender"):
        setattr(tr, name, MagicMock())
    return tr


def test_battery_percentage_math(reader):
    # (7700 - 7000) / 14 = 50
    reader.send_queue("@battery:7700")
    reader.batteryLvlSender.send.assert_called_once_with(50)


def test_battery_percentage_is_clamped(reader):
    reader.send_queue("@battery:100000")
    reader.batteryLvlSender.send.assert_called_once_with(100)


def test_battery_syntax_error_is_ignored(reader):
    reader.send_queue("@battery:syntax error")
    reader.batteryLvlSender.send.assert_not_called()


def test_brake_zeroes_speed_and_steer(reader):
    reader.send_queue("@brake:1")
    reader.currentSpeedSender.send.assert_called_once_with(0.0)
    reader.currentSteerSender.send.assert_called_once_with(0.0)


def test_speed_value_is_forwarded_as_float(reader):
    reader.send_queue("@speed:123.5")
    reader.currentSpeedSender.send.assert_called_once_with(123.5)


def test_imu_short_payload_is_treated_as_ack(reader):
    reader.send_queue("@imu:1")
    reader.imuAckSender.send.assert_called_once_with("1")
    reader.imuDataSender.send.assert_not_called()


def test_imu_full_payload_is_parsed_as_data(reader):
    reader.send_queue("@imu:1.0;2.0;3.0;4.0;5.0;6.0")
    reader.imuDataSender.send.assert_called_once()
    reader.imuAckSender.send.assert_not_called()


def test_vcdcalib_zero_signals_run_done(reader):
    reader.send_queue("@vcdCalib:0;0")
    reader.calibRunDoneSender.send.assert_called_once_with(True)
    reader.calibPWMDataSender.send.assert_not_called()


def test_vcdcalib_nonzero_sends_pwm_data(reader):
    reader.send_queue("@vcdCalib:100;200")
    reader.calibPWMDataSender.send.assert_called_once_with(
        {"speedPWM": "100", "steerPWM": "200"}
    )


def test_alive_signal(reader):
    reader.send_queue("@alive:1")
    reader.aliveSignalSender.send.assert_called_once_with(True)


def test_steer_limits_parsed(reader):
    reader.send_queue("@steerLimits:-250;250")
    reader.steeringLimitsSender.send.assert_called_once_with(
        {"lowerLimit": "-250", "upperLimit": "250"}
    )


def test_message_without_at_or_colon_is_ignored(reader):
    reader.send_queue("garbage")  # must not raise or send anything
    reader.batteryLvlSender.send.assert_not_called()


# --------------------------------------------------------------------------- #
# check_valid_value
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value,expected", [
    ("7700", True),
    ("syntax error", False),
    ("kl 15/30 is required!!", False),
    ("ack", False),
])
def test_check_valid_value(reader, value, expected):
    assert reader.check_valid_value("battery", value) is expected
