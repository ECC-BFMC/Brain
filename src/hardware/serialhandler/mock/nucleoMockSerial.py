import time
import threading


class NucleoMockSerial:
    """In-memory serial transport that mimics the NUCLEO serial protocol.

    The class intentionally implements only the subset of the pyserial API used
    by threadRead/threadWrite. It receives Raspberry Pi commands framed as
    #action:value;; and exposes NUCLEO-style responses framed as
    @action:value;; through read/in_waiting.
    """

    DEFAULT_PERIODS = {
        "battery": 1.0,
        "instant": 1.0,
        "imu": 0.15,
        "resourceMonitor": 5.0,
    }

    def __init__(self, telemetry_periods=None, clock=None):
        self.is_open = True
        self.device = "MOCK_NUCLEO"
        self._lock = threading.RLock()
        self._write_buffer = ""
        self._read_buffer = bytearray()
        self._clock = clock or time.monotonic
        self._periods = dict(self.DEFAULT_PERIODS)
        if telemetry_periods:
            self._periods.update(telemetry_periods)

        now = self._clock()
        self._next_telemetry = {
            name: now + period for name, period in self._periods.items()
        }
        self._kl_mode = 0
        self._speed = 0
        self._steer = 0
        self._battery_capacity = 6000
        self._telemetry_enabled = {
            "battery": False,
            "instant": False,
            "imu": False,
            "resourceMonitor": False,
        }

    @property
    def in_waiting(self):
        with self._lock:
            self._generate_due_telemetry()
            return len(self._read_buffer)

    def write(self, data):
        if not self.is_open:
            raise OSError("Mock serial port is closed")

        if isinstance(data, bytes):
            data = data.decode("ascii")

        with self._lock:
            self._write_buffer += data
            self._process_complete_commands()
            return len(data)

    def read(self, size=1):
        if not self.is_open:
            raise OSError("Mock serial port is closed")

        with self._lock:
            self._generate_due_telemetry()
            size = min(size, len(self._read_buffer))
            data = self._read_buffer[:size]
            del self._read_buffer[:size]
            return bytes(data)

    def close(self):
        with self._lock:
            self.is_open = False

    def reset_input_buffer(self):
        with self._lock:
            self._read_buffer.clear()

    def reset_output_buffer(self):
        with self._lock:
            self._write_buffer = ""

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
            self._enqueue(action, "syntax error")
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

        self._kl_mode = mode
        if mode == 0:
            self._speed = 0
            self._steer = 0
            for key in self._telemetry_enabled:
                self._telemetry_enabled[key] = False

        self._enqueue(action, str(mode))

    def _handle_speed(self, action, args):
        speed = self._single_int(args)
        if not self._requires_kl_30(action):
            return
        self._speed = self._clamp(speed, -500, 500)
        self._enqueue(action, str(self._speed))

    def _handle_steer(self, action, args):
        steer = self._single_int(args)
        if not self._requires_kl_30(action):
            return
        self._steer = self._clamp(steer, -250, 250)
        self._enqueue(action, str(self._steer))

    def _handle_brake(self, action, args):
        self._single_int(args)
        self._speed = 0
        self._steer = 0
        self._enqueue(action, "1")

    def _handle_vcd(self, action, args):
        speed, steer, duration = self._three_ints(args)
        if not self._requires_kl_30(action):
            return
        self._speed = self._clamp(speed, -500, 500)
        self._steer = self._clamp(steer, -250, 250)
        self._enqueue(action, f"{self._speed};{self._steer};{duration}")

    def _handle_vcdCalib(self, action, args):
        speed, steer, _duration = self._three_ints(args)
        if not self._requires_kl_30(action):
            return
        self._speed = self._clamp(speed, -500, 500)
        self._steer = self._clamp(steer, -250, 250)
        self._enqueue(action, "0;0")

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
        self._enqueue(action, "ack")

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

    def _generate_due_telemetry(self):
        if self._kl_mode not in (15, 30):
            return

        now = self._clock()
        for action, enabled in self._telemetry_enabled.items():
            if not enabled:
                continue
            period = self._periods[action]
            if now < self._next_telemetry[action]:
                continue
            self._enqueue(action, self._telemetry_value(action))
            self._next_telemetry[action] = now + period

    def _telemetry_value(self, action):
        if action == "battery":
            return "8400"
        if action == "instant":
            return "120"
        if action == "imu":
            return "0.000;0.000;0.000;0.000;0.000;9.810"
        if action == "resourceMonitor":
            return "Heap (12.50);Stack (8.25)"
        raise ValueError(action)

    def _enqueue(self, action, value):
        self._read_buffer.extend(f"@{action}:{value};;\r\n".encode("ascii"))

    def _single_int(self, args):
        if len(args) != 1:
            raise ValueError("Expected one argument")
        return int(args[0])

    def _three_ints(self, args):
        if len(args) != 3:
            raise ValueError("Expected three arguments")
        return int(args[0]), int(args[1]), int(args[2])

    @staticmethod
    def _clamp(value, lower, upper):
        return max(lower, min(upper, value))
