import random
import threading
import time

from . import tools


class SerialException(OSError):
    """Simulator equivalent of serial.SerialException."""


class Serial:
    """Pyserial-compatible simulation of the BFMC NUCLEO firmware."""

    DEFAULT_PERIODS = {
        "battery": 3.0,
        "instant": 1.0,
        "imu": 0.15,
        "resourceMonitor": 5.0,
    }
    POWER_PERIOD = 0.1
    WARNING_VOLTAGE = 7200
    BATTERY_EMPTY_VOLTAGE = 7000
    WARNING_TICKS = 250

    SPEED_VALUES_POSITIVE = (
        40, 50, 60, 70, 80, 90, 100, 110, 120, 130,
        140, 150, 160, 170, 180, 190, 200, 210, 220, 260,
        300, 350, 400, 450, 500,
    )
    SPEED_VALUES_NEGATIVE = tuple(-value for value in SPEED_VALUES_POSITIVE)
    SPEED_PWM_POSITIVE = (
        1576, 1579, 1582, 1584, 1587, 1590, 1593, 1594, 1594, 1597,
        1600, 1602, 1603, 1606, 1609, 1612, 1611, 1612, 1614, 1621,
        1635, 1638, 1643, 1653, 1661,
    )
    SPEED_PWM_NEGATIVE = (
        1405, 1403, 1399, 1397, 1395, 1392, 1389, 1387, 1387, 1384,
        1381, 1380, 1379, 1375, 1372, 1369, 1371, 1369, 1367, 1361,
        1347, 1344, 1339, 1329, 1321,
    )
    STEER_VALUES_POSITIVE = (0, 150, 200)
    STEER_VALUES_NEGATIVE = (0, -150, -200)
    STEER_PWM_POSITIVE = (1500, 1801, 1914)
    STEER_PWM_NEGATIVE = (1500, 1285, 1154)

    def __init__(
        self,
        port=None,
        baudrate=9600,
        timeout=None,
        telemetry_periods=None,
        clock=None,
        battery_voltage=None,
        instant_consumption=None,
        imu_values=None,
        resource_usage=None,
        rng=None,
    ):
        self.is_open = True
        self.port = port
        self.device = port
        self.name = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._lock = threading.RLock()
        self._write_buffer = ""
        self._read_buffer = bytearray()
        self._clock = clock or time.monotonic
        self._random = rng or random.Random()
        self._periods = dict(self.DEFAULT_PERIODS)
        if telemetry_periods:
            self._periods.update(telemetry_periods)

        self._kl_mode = 0
        self._speed = 0
        self._steer = 0
        self._battery_capacity = 6000
        self._randomize_battery = battery_voltage is None
        self._randomize_instant = instant_consumption is None
        self._randomize_imu = imu_values is None
        self._randomize_resources = resource_usage is None
        self._battery_voltage = 8200 if battery_voltage is None else int(battery_voltage)
        self._instant_consumption = 4800 if instant_consumption is None else int(instant_consumption)
        self._imu_values = tuple(
            (1.0, 2.0, 3.0, 0.1, 0.2, 0.3) if imu_values is None else imu_values
        )
        self._resource_usage = tuple(
            (12.34, 8.76) if resource_usage is None else resource_usage
        )
        self._telemetry_enabled = {name: False for name in self._periods}
        self._motion = None
        self._warning_ticks = 0
        self._warning_sent = False
        self._alert_id = 0

        now = self._clock()
        self._next_telemetry = {
            name: now + period for name, period in self._periods.items()
        }
        self._next_power_check = now + self.POWER_PERIOD

    @property
    def in_waiting(self):
        with self._lock:
            self._generate_due_events()
            return len(self._read_buffer)

    @property
    def kl_mode(self):
        return self._kl_mode

    @property
    def speed(self):
        return self._speed

    @property
    def steer(self):
        return self._steer

    @property
    def alert_id(self):
        return self._alert_id

    def write(self, data):
        if not self.is_open:
            raise SerialException("Simulated serial port is closed")
        if isinstance(data, (bytes, bytearray, memoryview)):
            data = bytes(data).decode("ascii")
        if not isinstance(data, str):
            raise TypeError("Serial.write expects bytes-like or ASCII string data")

        with self._lock:
            self._write_buffer += data
            self._process_complete_commands()
            return len(data)

    def read(self, size=1):
        if not self.is_open:
            raise SerialException("Simulated serial port is closed")

        with self._lock:
            self._generate_due_events()
            size = min(max(0, int(size)), len(self._read_buffer))
            data = self._read_buffer[:size]
            del self._read_buffer[:size]
            return bytes(data)

    def close(self):
        with self._lock:
            self.is_open = False

    def open(self):
        with self._lock:
            self.is_open = True

    def reset_input_buffer(self):
        with self._lock:
            self._read_buffer.clear()

    def reset_output_buffer(self):
        with self._lock:
            self._write_buffer = ""

    def set_battery_voltage(self, millivolts):
        with self._lock:
            self._battery_voltage = max(0, int(millivolts))
            self._randomize_battery = False
            self._warning_ticks = 0
            self._warning_sent = False

    def set_instant_consumption(self, milliamps):
        with self._lock:
            self._instant_consumption = max(0, int(milliamps))
            self._randomize_instant = False

    def set_imu_values(self, roll, pitch, yaw, velocity_x, velocity_y, velocity_z):
        with self._lock:
            self._imu_values = (roll, pitch, yaw, velocity_x, velocity_y, velocity_z)
            self._randomize_imu = False

    def set_resource_usage(self, heap_percent, stack_percent):
        with self._lock:
            self._resource_usage = (heap_percent, stack_percent)
            self._randomize_resources = False

    def _process_complete_commands(self):
        while ";;" in self._write_buffer:
            raw_command, self._write_buffer = self._write_buffer.split(";;", 1)
            raw_command = raw_command.strip()
            if raw_command:
                self._handle_command(raw_command)

    def _handle_command(self, raw_command):
        if not raw_command.startswith("#") or ":" not in raw_command:
            return

        action, raw_values = raw_command[1:].split(":", 1)
        values = raw_values.strip().strip(";")
        args = [] if values == "" else values.split(";")
        handler = getattr(self, f"_handle_{action}", None)

        if handler is None:
            return

        try:
            handler(action, args)
        except (TypeError, ValueError):
            self._enqueue(action, "syntax error")

    def _handle_kl(self, action, args):
        mode = self._single_int(args)
        if mode not in (0, 15, 30):
            self._enqueue(action, "syntax error")
            return
        previous_mode = self._kl_mode
        self._kl_mode = mode
        self._enqueue(action, str(mode))

        if mode == 0:
            self._motion = None
            self._speed = 0
            self._steer = 0
            self._alert_id = 3
            for name in self._telemetry_enabled:
                self._telemetry_enabled[name] = False
            if previous_mode != 0:
                self._enqueue("brake", "1")
            return

        self._alert_id = 2 if mode == 30 else 4
        now = self._clock()
        for name, period in self._periods.items():
            self._telemetry_enabled[name] = True
            self._next_telemetry[name] = now + period

        if previous_mode == 0:
            self._speed = 0
            self._steer = 0
            self._enqueue("brake", "1")

    def _handle_speed(self, action, args):
        speed = self._single_int(args)
        if not self._requires_kl_30(action):
            return
        self._motion = None
        self._speed = self._clamp(speed, -500, 500)
        self._enqueue(action, str(self._speed))

    def _handle_steer(self, action, args):
        steer = self._single_int(args)
        if not self._requires_kl_30(action):
            return
        self._motion = None
        self._steer = self._clamp(steer, -250, 250)
        self._enqueue(action, str(self._steer))

    def _handle_brake(self, action, args):
        steer = self._single_int(args)
        self._motion = None
        self._speed = 0
        self._steer = self._clamp(steer, -250, 250)
        self._enqueue(action, "1")

    def _handle_vcd(self, action, args):
        speed, steer, duration = self._three_ints(args)
        if not self._requires_kl_30(action):
            return
        if not (-500 <= speed <= 500 and -232 <= steer <= 232 and 0 <= duration <= 255):
            self._enqueue(action, "something went wrong")
            return
        self._speed = speed
        self._steer = steer
        self._start_motion(action, duration)
        self._enqueue(action, f"{speed};{steer};{duration}")

    def _handle_vcdCalib(self, action, args):
        speed, steer, duration = self._three_ints(args)
        if not self._requires_kl_30(action):
            return
        if not (-500 <= speed <= 500 and -272 <= steer <= 272 and 0 <= duration <= 255):
            self._enqueue(action, "something went wrong")
            return
        self._speed = speed
        self._steer = steer
        self._start_motion(action, duration)
        self._enqueue(action, f"{self._speed_pwm(speed)};{self._steer_pwm(steer)}")

    def _handle_alive(self, action, args):
        self._single_int(args)
        self._enqueue(action, "1")

    def _handle_steerLimits(self, action, args):
        self._single_int(args)
        self._enqueue(action, "-250;250")

    def _handle_batteryCapacity(self, action, args):
        self._battery_capacity = self._single_int(args)
        self._enqueue(action, "ack")

    def _handle_battery(self, action, args):
        self._set_toggle(action, args)

    def _handle_instant(self, action, args):
        self._set_toggle(action, args)

    def _handle_imu(self, action, args):
        self._set_toggle(action, args)

    def _handle_resourceMonitor(self, action, args):
        self._set_toggle(action, args)

    def _set_toggle(self, action, args):
        activate = self._single_int(args)
        if not self._requires_kl_15_or_30(action):
            return
        self._telemetry_enabled[action] = activate >= 1
        if activate >= 1:
            self._next_telemetry[action] = self._clock() + self._periods[action]
        self._enqueue(action, "1")

    def _requires_kl_30(self, action):
        if self._kl_mode != 30:
            self._enqueue(action, "kl 30 is required!!")
            return False
        return True

    def _requires_kl_15_or_30(self, action):
        if self._kl_mode not in (15, 30):
            self._enqueue(action, "kl 15/30 is required!!")
            return False
        return True

    def _start_motion(self, action, duration_deciseconds):
        self._motion = {
            "action": action,
            "deadline": self._clock() + (duration_deciseconds / 10.0) + 0.001,
        }

    def _generate_due_events(self):
        now = self._clock()
        self._complete_motion(now)
        self._generate_due_telemetry(now)
        self._run_power_manager(now)

    def _complete_motion(self, now):
        if self._motion is None or now < self._motion["deadline"]:
            return
        action = self._motion["action"]
        self._motion = None
        self._speed = 0
        self._steer = 0
        completion = "0;0;0" if action == "vcd" else "0;0"
        self._enqueue(action, completion)

    def _generate_due_telemetry(self, now):
        if self._kl_mode not in (15, 30):
            return
        for action, enabled in self._telemetry_enabled.items():
            if not enabled:
                continue
            period = self._periods[action]
            if now < self._next_telemetry[action]:
                continue
            self._enqueue(action, self._telemetry_value(action))
            elapsed_periods = int((now - self._next_telemetry[action]) / period) + 1
            self._next_telemetry[action] += elapsed_periods * period

    def _run_power_manager(self, now):
        if now < self._next_power_check:
            return
        elapsed_ticks = int((now - self._next_power_check) / self.POWER_PERIOD) + 1
        self._next_power_check += elapsed_ticks * self.POWER_PERIOD

        if self.BATTERY_EMPTY_VOLTAGE < self._battery_voltage <= self.WARNING_VOLTAGE:
            self._warning_ticks += elapsed_ticks
            if self._warning_ticks >= self.WARNING_TICKS and not self._warning_sent:
                self._warning_sent = True
                self._alert_id = 1
                hours, minutes, seconds = self._estimated_shutdown_time()
                self._enqueue("warning", f"{hours}:{minutes}:{seconds}")
            return


        self._warning_ticks = 0
        self._warning_sent = False

    def _estimated_shutdown_time(self):
        if self._instant_consumption <= 0:
            return 0, 0, 0
        remaining_milliamps = (
            (self._battery_voltage - self.BATTERY_EMPTY_VOLTAGE)
            * self._battery_capacity
            / 8400
        )
        total_seconds = max(
            0,
            int((remaining_milliamps / self._instant_consumption) * 3600),
        )
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return min(hours, 255), minutes, seconds

    def _telemetry_value(self, action):
        if action == "battery":
            value = (
                self._random.randint(8000, 8400)
                if self._randomize_battery
                else self._battery_voltage
            )
            return str(value)
        if action == "instant":
            value = (
                self._random.randint(4000, 5500)
                if self._randomize_instant
                else self._instant_consumption
            )
            return str(value)
        if action == "imu":
            values = (
                tuple(self._random.uniform(0, 10) for _ in range(6))
                if self._randomize_imu
                else self._imu_values
            )
            return ";".join(f"{float(value):.3f}" for value in values)
        if action == "resourceMonitor":
            heap, stack = (
                (self._random.uniform(0, 100), self._random.uniform(0, 100))
                if self._randomize_resources
                else self._resource_usage
            )
            return f"Heap ({float(heap):.2f});Stack ({float(stack):.2f})"
        raise ValueError(action)

    def _enqueue(self, action, value):
        self._read_buffer.extend(f"@{action}:{value};;\r\n".encode("ascii"))

    def _speed_pwm(self, speed):
        value = -speed
        if value == 0:
            return 1491
        if value >= self.SPEED_VALUES_POSITIVE[-1]:
            return self.SPEED_PWM_POSITIVE[-1]
        if value <= self.SPEED_VALUES_NEGATIVE[-1]:
            return self.SPEED_PWM_NEGATIVE[-1]
        if value <= self.SPEED_VALUES_POSITIVE[0]:
            if value > 0:
                return self.SPEED_PWM_POSITIVE[0]
            if value >= self.SPEED_VALUES_NEGATIVE[0]:
                return self.SPEED_PWM_NEGATIVE[0]
            return self._interpolate_table(value, self.SPEED_VALUES_NEGATIVE, self.SPEED_PWM_NEGATIVE)
        return self._interpolate_table(value, self.SPEED_VALUES_POSITIVE, self.SPEED_PWM_POSITIVE)

    def _steer_pwm(self, steer):
        if steer == 0:
            return self.STEER_PWM_POSITIVE[0]
        if steer >= self.STEER_VALUES_POSITIVE[-1]:
            return self.STEER_PWM_POSITIVE[-1]
        if steer <= self.STEER_VALUES_NEGATIVE[-1]:
            return self.STEER_PWM_NEGATIVE[-1]
        if steer < 0:
            return self._interpolate_table(steer, self.STEER_VALUES_NEGATIVE, self.STEER_PWM_NEGATIVE)
        return self._interpolate_table(steer, self.STEER_VALUES_POSITIVE, self.STEER_PWM_POSITIVE)

    @staticmethod
    def _interpolate_table(value, references, pwm_values):
        scale = 1000
        for index in range(1, len(references)):
            if (
                references[index - 1] <= value <= references[index]
                or references[index - 1] >= value >= references[index]
            ):
                delta_pwm = (pwm_values[index] - pwm_values[index - 1]) * scale
                delta_value = references[index] - references[index - 1]
                slope = int(delta_pwm / delta_value)
                interpolated = pwm_values[index - 1] * scale + slope * (value - references[index - 1])
                return int(interpolated / scale)
        return pwm_values[0]

    @staticmethod
    def _single_int(args):
        if len(args) != 1:
            raise ValueError("Expected one argument")
        return int(args[0])

    @staticmethod
    def _three_ints(args):
        if len(args) != 3:
            raise ValueError("Expected three arguments")
        return int(args[0]), int(args[1]), int(args[2])

    @staticmethod
    def _clamp(value, lower, upper):
        return max(lower, min(upper, value))
