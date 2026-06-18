import logging
import contextlib
import io
import sys
import types
import unittest
from queue import Empty, Queue

serial_module = types.ModuleType("serial")
serial_module.SerialException = Exception
serial_tools_module = types.ModuleType("serial.tools")
serial_list_ports_module = types.ModuleType("serial.tools.list_ports")
serial_tools_module.list_ports = serial_list_ports_module
serial_module.tools = serial_tools_module
sys.modules.setdefault("serial", serial_module)
sys.modules.setdefault("serial.tools", serial_tools_module)
sys.modules.setdefault("serial.tools.list_ports", serial_list_ports_module)

from src.hardware.serialhandler.mock.nucleoMockSerial import NucleoMockSerial
from src.hardware.serialhandler.processSerialHandler import processSerialHandler
from src.hardware.serialhandler.threads.threadRead import threadRead
from src.utils.messages.allMessages import (
    AliveSignal,
    BatteryLvl,
    CurrentSpeed,
    CurrentSteer,
    InstantConsumption,
    ResourceMonitor,
    SteeringLimits,
)


class ManualClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def make_queue_list():
    return {
        "Critical": Queue(),
        "Warning": Queue(),
        "General": Queue(),
        "Config": Queue(),
        "Log": Queue(),
    }


def read_all(serial_con):
    waiting = serial_con.in_waiting
    return serial_con.read(waiting).decode("ascii")


class NucleoMockSerialTests(unittest.TestCase):
    def test_fragmented_write_and_core_responses(self):
        serial_con = NucleoMockSerial()

        serial_con.write(b"#kl:30;")
        self.assertEqual(0, serial_con.in_waiting)
        serial_con.write(b";\r\n#speed:700;;\r\n#steer:-300;;\r\n")

        output = read_all(serial_con)

        self.assertIn("@kl:30;;\r\n", output)
        self.assertIn("@speed:500;;\r\n", output)
        self.assertIn("@steer:-250;;\r\n", output)

    def test_speed_requires_kl_30(self):
        serial_con = NucleoMockSerial()

        serial_con.write(b"#speed:100;;\r\n")

        self.assertEqual("@speed:kl 30 is required!!;;\r\n", read_all(serial_con))

    def test_telemetry_requires_toggle_and_kl(self):
        clock = ManualClock()
        serial_con = NucleoMockSerial(
            telemetry_periods={"battery": 1.0},
            clock=clock,
        )

        serial_con.write(b"#kl:15;;\r\n#battery:1;;\r\n")
        read_all(serial_con)
        clock.advance(1.0)

        self.assertIn("@battery:8400;;\r\n", read_all(serial_con))

        serial_con.write(b"#kl:0;;\r\n")
        read_all(serial_con)
        clock.advance(10.0)

        self.assertEqual("", read_all(serial_con))

    def test_vcd_calib_completes_immediately(self):
        serial_con = NucleoMockSerial()

        serial_con.write(b"#kl:30;;\r\n#vcdCalib:100;20;5;;\r\n")

        self.assertIn("@vcdCalib:0;0;;\r\n", read_all(serial_con))

    def test_close_and_reset_buffers(self):
        serial_con = NucleoMockSerial()
        serial_con.write(b"#alive:0;;\r\n")

        serial_con.reset_input_buffer()
        self.assertEqual("", read_all(serial_con))

        serial_con.write(b"#kl:3")
        serial_con.reset_output_buffer()
        serial_con.write(b"#alive:0;;\r\n")
        self.assertEqual("@alive:1;;\r\n", read_all(serial_con))

        serial_con.close()
        with self.assertRaises(OSError):
            serial_con.write(b"#alive:0;;\r\n")


class ThreadReadParserTests(unittest.TestCase):
    def make_reader(self):
        queues = make_queue_list()
        reader = threadRead.__new__(threadRead)
        reader.queuesList = queues
        reader.logger = logging.getLogger("test")
        reader.debugger = False
        reader.warningPattern = r'^(-?[0-9]+)H(-?[0-5]?[0-9])M(-?[0-5]?[0-9])S$'
        reader.resourceMonitorPattern = r'Heap \((\d+\.\d+)\);Stack \((\d+\.\d+)\)'
        reader._init_senders()
        return reader, queues

    def get_message(self, queues, message):
        skipped = []
        while True:
            try:
                queued = queues["General"].get_nowait()
            except Empty:
                for item in skipped:
                    queues["General"].put(item)
                break

            if (
                queued["Owner"] == message.Owner.value
                and queued["msgID"] == message.msgID.value
            ):
                for item in skipped:
                    queues["General"].put(item)
                return queued["msgValue"]
            skipped.append(queued)
        self.fail(f"Missing message {message}")

    def test_mock_responses_parse_into_existing_messages(self):
        reader, queues = self.make_reader()

        reader.send_queue("@speed:123")
        reader.send_queue("@steer:-20")
        reader.send_queue("@alive:1")
        reader.send_queue("@steerLimits:-250;250")
        reader.send_queue("@battery:8400")
        reader.send_queue("@instant:120")
        reader.send_queue("@resourceMonitor:Heap (12.50);Stack (8.25)")

        self.assertEqual(123.0, self.get_message(queues, CurrentSpeed))
        self.assertEqual(-20.0, self.get_message(queues, CurrentSteer))
        self.assertIs(True, self.get_message(queues, AliveSignal))
        self.assertEqual(
            {"lowerLimit": "-250", "upperLimit": "250"},
            self.get_message(queues, SteeringLimits),
        )
        self.assertEqual(100, self.get_message(queues, BatteryLvl))
        self.assertEqual(120.0, self.get_message(queues, InstantConsumption))
        self.assertEqual(
            {"heap": "12.50", "stack": "8.25"},
            self.get_message(queues, ResourceMonitor),
        )


class ProcessSerialHandlerMockModeTests(unittest.TestCase):
    def test_mock_mode_connects_without_scanning_ports(self):
        queues = make_queue_list()
        process = processSerialHandler(
            queues,
            logging.getLogger("test"),
            use_mock=True,
        )
        process.serialLock = __import__("threading").Lock()

        def fail_if_called():
            raise AssertionError("Mock mode must not scan hardware serial ports")

        serial_list_ports_module.comports = fail_if_called

        with contextlib.redirect_stdout(io.StringIO()):
            process._try_serial_connection()

        self.assertTrue(process.serialConnected)
        self.assertEqual("MOCK_NUCLEO", process.serialDevice)
        self.assertIsInstance(process.serialCon, NucleoMockSerial)


if __name__ == "__main__":
    unittest.main()
