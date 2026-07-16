import random
import re
import sys
import types
from queue import Queue
from threading import Lock

import pytest

import src.hardware.serialhandler.processSerialHandler as serial_process_module
from sim import serial
from src.hardware.serialhandler.processSerialHandler import processSerialHandler


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def read_available(port):
    waiting = port.in_waiting
    if waiting == 0:
        return ""
    return port.read(waiting).decode("ascii")


def send(port, command):
    port.write(command.encode("ascii"))
    return read_available(port)


def make_queues():
    return {name: Queue() for name in ("Critical", "Warning", "General", "Config")}


def test_dev_selection_ignores_an_installed_serial_module(monkeypatch):
    installed_serial = types.ModuleType("serial")
    monkeypatch.setitem(sys.modules, "serial", installed_serial)

    selected_module = serial_process_module._load_serial(use_simulator=True)
    assert selected_module is serial


def test_simulated_port_discovery_and_connection_api():
    ports = serial.tools.list_ports.comports()
    assert [port.device for port in ports] == ["/dev/ttyACM0"]

    connection = serial.Serial(ports[0].device, 115200, timeout=0.1)
    assert connection.is_open
    assert connection.port == "/dev/ttyACM0"
    assert connection.baudrate == 115200
    assert connection.timeout == 0.1

    connection.close()
    assert not connection.is_open
    connection.open()
    assert connection.is_open


def test_serial_process_uses_normal_discovery_with_simulator():
    process = processSerialHandler(make_queues(), dev_mode=True)
    assert process.serial is None
    process.serialLock = Lock()
    process._try_serial_connection()
    try:
        assert process.serialConnected
        assert process.serialDevice == "/dev/ttyACM0"
        assert isinstance(process.serialCon, serial.Serial)
    finally:
        process._safe_close_serial()


def test_kl_modes_and_motor_commands():
    connection = serial.Serial("/dev/ttyACM0", 115200)

    assert "@speed:kl 30 is required!!;;" in send(connection, "#speed:100;;")
    assert "@kl:30;;" in send(connection, "#kl:30;;")
    assert "@speed:500;;" in send(connection, "#speed:900;;")
    assert "@steer:-250;;" in send(connection, "#steer:-900;;")
    assert "@brake:1;;" in send(connection, "#brake:0;;")

    response = send(connection, "#kl:0;;")
    assert "@kl:0;;" in response
    assert connection._speed == 0
    assert connection._steer == 0


def test_combined_control_calibration_and_queries():
    connection = serial.Serial("/dev/ttyACM0", 115200)
    send(connection, "#kl:30;;")

    assert "@vcd:100;-200;7;;" in send(connection, "#vcd:100;-200;7;;")
    assert "@vcdCalib:1389;1914;;" in send(connection, "#vcdCalib:100;200;7;;")
    assert "@alive:1;;" in send(connection, "#alive:0;;")
    assert "@steerLimits:-250;250;;" in send(connection, "#steerLimits:0;;")
    assert "@batteryCapacity:ack;;" in send(connection, "#batteryCapacity:7200;;")


def test_telemetry_toggles_emit_values_using_elapsed_time():
    clock = FakeClock()
    connection = serial.Serial(
        "/dev/ttyACM0",
        telemetry_periods={"battery": 1.0, "instant": 1.0, "imu": 1.0, "resourceMonitor": 1.0},
        clock=clock,
    )
    send(connection, "#kl:15;;")
    for action in ("battery", "instant", "imu", "resourceMonitor"):
        assert f"@{action}:1;;" in send(connection, f"#{action}:1;;")

    assert read_available(connection) == ""
    clock.advance(1.0)
    telemetry = read_available(connection)

    assert re.search(r"@battery:\d+;;", telemetry)
    assert re.search(r"@instant:\d+;;", telemetry)
    assert re.search(r"@imu:(?:\d+\.\d{3};){5}\d+\.\d{3};;", telemetry)
    assert re.search(r"@resourceMonitor:Heap \(\d+\.\d{2}\);Stack \(\d+\.\d{2}\);;", telemetry)


def test_telemetry_can_be_disabled_and_kl_zero_disables_all_streams():
    clock = FakeClock()
    connection = serial.Serial(
        "/dev/ttyACM0",
        telemetry_periods={name: 1.0 for name in serial.Serial.DEFAULT_PERIODS},
        clock=clock,
    )
    send(connection, "#kl:15;;")
    for action in serial.Serial.DEFAULT_PERIODS:
        send(connection, f"#{action}:0;;")
    clock.advance(1.0)
    assert read_available(connection) == ""

    send(connection, "#battery:1;;")
    send(connection, "#kl:0;;")
    clock.advance(1.0)
    assert read_available(connection) == ""


def test_invalid_commands_return_syntax_errors():
    connection = serial.Serial("/dev/ttyACM0")
    assert "@kl:syntax error;;" in send(connection, "#kl:99;;")
    assert send(connection, "#unknown:1;;") == ""
    assert "@speed:syntax error;;" in send(connection, "#speed:not-a-number;;")


def test_partial_writes_and_buffer_resets():
    connection = serial.Serial("/dev/ttyACM0")
    connection.write(b"#kl:")
    assert connection.in_waiting == 0
    connection.write(b"30;;")
    assert "@kl:30;;" in read_available(connection)

    connection.write(b"#speed:")
    connection.reset_output_buffer()
    connection.write(b"100;;")
    assert connection.in_waiting == 0

    send(connection, "#alive:0;;")
    connection.reset_input_buffer()
    assert connection.in_waiting == 0


def test_closed_port_raises_serial_exception():
    connection = serial.Serial("/dev/ttyACM0")
    connection.close()

    with pytest.raises(serial.SerialException):
        connection.write(b"#alive:0;;")
    with pytest.raises(serial.SerialException):
        connection.read()


def test_vcd_uses_delta_time_and_reports_completion():
    clock = FakeClock()
    connection = serial.Serial("/dev/ttyACM0", clock=clock)
    send(connection, "#kl:30;;")

    assert "@vcd:100;20;5;;" in send(connection, "#vcd:100;20;5;;")
    assert (connection.speed, connection.steer) == (100, 20)

    clock.advance(0.5)
    assert "@vcd:0;0;0;;" not in read_available(connection)
    clock.advance(0.002)
    assert "@vcd:0;0;0;;" in read_available(connection)
    assert (connection.speed, connection.steer) == (0, 0)


def test_vcd_and_calibration_enforce_firmware_ranges():
    connection = serial.Serial("/dev/ttyACM0")
    send(connection, "#kl:30;;")

    assert "@vcd:something went wrong;;" in send(connection, "#vcd:501;0;1;;")
    assert "@vcd:something went wrong;;" in send(connection, "#vcd:0;233;1;;")
    assert "@vcdCalib:something went wrong;;" in send(connection, "#vcdCalib:0;273;1;;")


def test_calibration_reports_pwm_and_finishes_using_delta_time():
    clock = FakeClock()
    connection = serial.Serial("/dev/ttyACM0", clock=clock)
    send(connection, "#kl:30;;")

    assert "@vcdCalib:1389;1914;;" in send(connection, "#vcdCalib:100;200;2;;")
    clock.advance(0.202)
    assert "@vcdCalib:0;0;;" in read_available(connection)


def test_kl_automatically_enables_all_firmware_telemetry_periods():
    clock = FakeClock()
    connection = serial.Serial("/dev/ttyACM0", clock=clock)
    send(connection, "#kl:15;;")

    clock.advance(0.15)
    assert "@imu:" in read_available(connection)

    clock.advance(0.85)
    assert re.search(r"@instant:\d+;;", read_available(connection))

    clock.advance(2.0)
    assert re.search(r"@battery:\d+;;", read_available(connection))

    clock.advance(2.0)
    assert re.search(
        r"@resourceMonitor:Heap \(\d+\.\d{2}\);Stack \(\d+\.\d{2}\);;",
        read_available(connection),
    )


def test_default_sensor_values_vary_within_the_old_mock_ranges():
    clock = FakeClock()
    connection = serial.Serial(
        "/dev/ttyACM0",
        clock=clock,
        telemetry_periods={name: 1.0 for name in serial.Serial.DEFAULT_PERIODS},
        rng=random.Random(1234),
    )
    send(connection, "#kl:15;;")

    samples = []
    for _ in range(2):
        clock.advance(1.0)
        samples.append(read_available(connection))

    batteries = [int(re.search(r"@battery:(\d+);;", sample).group(1)) for sample in samples]
    currents = [int(re.search(r"@instant:(\d+);;", sample).group(1)) for sample in samples]
    assert all(8000 <= value <= 8400 for value in batteries)
    assert all(4000 <= value <= 5500 for value in currents)
    assert batteries[0] != batteries[1]
    assert currents[0] != currents[1]

    imu_values = [
        float(value)
        for value in re.search(r"@imu:([^@]+);;\r\n", samples[0]).group(1).split(";")
    ]
    resources = re.search(
        r"@resourceMonitor:Heap \((\d+\.\d{2})\);Stack \((\d+\.\d{2})\);;",
        samples[0],
    )
    assert len(imu_values) == 6
    assert all(0 <= value <= 10 for value in imu_values)
    assert all(0 <= float(resources.group(index)) <= 100 for index in (1, 2))

def test_simulated_sensor_values_are_configurable():
    clock = FakeClock()
    connection = serial.Serial(
        "/dev/ttyACM0",
        clock=clock,
        telemetry_periods={name: 1.0 for name in serial.Serial.DEFAULT_PERIODS},
    )
    connection.set_battery_voltage(8123)
    connection.set_instant_consumption(456)
    connection.set_imu_values(6, 5, 4, 0.6, 0.5, 0.4)
    connection.set_resource_usage(22.2, 33.3)
    send(connection, "#kl:15;;")

    clock.advance(1.0)
    telemetry = read_available(connection)
    assert "@battery:8123;;" in telemetry
    assert "@instant:456;;" in telemetry
    assert "@imu:6.000;5.000;4.000;0.600;0.500;0.400;;" in telemetry
    assert "@resourceMonitor:Heap (22.20);Stack (33.30);;" in telemetry


def test_brake_preserves_the_requested_clamped_steering_angle():
    connection = serial.Serial("/dev/ttyACM0")
    send(connection, "#kl:30;;")
    send(connection, "#speed:100;;")

    assert "@brake:1;;" in send(connection, "#brake:900;;")
    assert connection.speed == 0
    assert connection.steer == 250


def test_low_battery_warning_matches_firmware_format():
    clock = FakeClock()
    connection = serial.Serial(
        "/dev/ttyACM0",
        clock=clock,
        battery_voltage=7100,
        instant_consumption=1000,
    )

    clock.advance(25.1)
    assert "@warning:0:4:17;;" in read_available(connection)
    assert connection.alert_id == 1

