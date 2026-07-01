# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")

import re
import serial
import serial.tools.list_ports
import threading
from threading import Lock

from src.templates.workerprocess import WorkerProcess
from src.hardware.serialhandler.mock.nucleoMockSerial import NucleoMockSerial
from src.hardware.serialhandler.threads.threadRead import threadRead
from src.hardware.serialhandler.threads.threadWrite import threadWrite
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.statemachine.systemMode import SystemMode
from src.utils.messages.allMessages import StateChange, SerialConnectionState
from src.utils.logConfig import get_logger

class processSerialHandler(WorkerProcess):
    """This process handle connection between NUCLEO and Raspberry PI.\n
    Args:
        queueList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
        debugging (bool, optional): A flag for debugging. Defaults to False.
        example (bool, optional): A flag for running the example. Defaults to False.
    """

    # ===================================== INIT =========================================
    def __init__(self, queueList, ready_event=None, dashboard_ready=None, debugging=False, example=False, use_mock=False):
        # devFile = "/dev/ttyACM0"
        self.logger = get_logger("Serial Handler")
        self.queuesList = queueList
        self.debugging = debugging
        self.example = example
        self.dashboard_ready = dashboard_ready
        self.use_mock = use_mock

        # comm init
        self.serialCon = None
        self.serialConnected = False
        self.serialDevice = None
        self.serialLock = None
        self.reconnecting = False

        self._init_subscribers()
        self._init_senders()

        super(processSerialHandler, self).__init__(self.queuesList, ready_event)

    def _init_subscribers(self):
        self.stateChangeSubscriber = messageHandlerSubscriber(self.queuesList, StateChange, "lastOnly", True)
        self.serialConnectionStateSubscriber = messageHandlerSubscriber(self.queuesList, SerialConnectionState, "lastOnly", True)

    def _init_senders(self):
        self.serialConnectedSender = messageHandlerSender(self.queuesList, SerialConnectionState)

    def _safe_close_serial(self):
        """Safely close the serial connection with proper error handling."""
        if self.serialCon and hasattr(self.serialCon, 'is_open') and self.serialCon.is_open:
            try:
                self.serialCon.close()
            except (OSError, serial.SerialException) as e:
                self.logger.warning(f"Error closing serial connection: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error closing serial: {e}")

    def _try_serial_connection(self):
        """Try to connect to the serial device."""
        with self.serialLock:
            if self.use_mock:
                self._safe_close_serial()
                self.serialDevice = "MOCK_NUCLEO"
                self.serialCon = NucleoMockSerial()
                self.serialConnected = True
                self.logger.info(f"Connected to {self.serialDevice}")
                return

            try:
                # clean up existing connection safely
                self._safe_close_serial()

                self.serialDevice = next((port.device for port in serial.tools.list_ports.comports() if re.match(r"/dev/ttyACM\d+", port.device)), None)
                self.serialCon = serial.Serial(self.serialDevice, 115200, timeout=0.1)
                self.serialCon.reset_input_buffer()
                self.serialCon.reset_output_buffer()
                self.serialConnected = True
                self.logger.info(f"Connected to {self.serialDevice}")

            except (serial.SerialException, FileNotFoundError):
                self._safe_close_serial()
                self.serialCon = None
                self.serialConnected = False

    def _try_reconnect(self):
        """Try to reconnect to serial device (called by timer)."""
        if self.use_mock:
            return

        if self.reconnecting:
            return # another reconnection attempt is already in progress

        self.reconnecting = True

        self._try_serial_connection()

        if self.serialConnected:
            # reset thread error states after successful reconnection
            self.serialConnectedSender.send(True)
            self._reset_thread_error_states()
            self.resume_threads()
            self.reconnecting = False
        else:
            # schedule next attempt
            self.reconnecting = False
            threading.Timer(1, self._try_reconnect).start()

    def _reset_thread_error_states(self):
        """Reset error states in threads after successful reconnection."""
        if self.threads:
            for thread in self.threads:
                if hasattr(thread, 'last_error_time'):
                    thread.last_error_time = None

    def _wait_for_dashboard_and_notify(self):
        """Wait for dashboard to be ready, then notify connected state once without blocking init."""
        self.dashboard_ready.wait()
        if self.dashboard_ready.is_set():
            self.serialConnectedSender.send(self.serialConnected)


    def _handle_serial_disconnection(self):
        """Handle serial disconnection by pausing threads and starting reconnection."""
        if self.use_mock:
            return

        with self.serialLock:
            # check if already handling disconnection
            if self.reconnecting or not self.serialConnected:
                return

            self.logger.warning("Serial device disconnected")

            # mark as disconnected
            self.serialConnected = False

            # clean up serial connection safely
            self._safe_close_serial()

            self.serialCon = None

            if self.threads:
                self.pause_threads()

            threading.Timer(1, self._try_reconnect).start()

    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializing methods and start the threads."""
        self.serialLock = Lock()
        self._try_serial_connection()

        if not self.serialConnected:
            self.logger.warning("No serial connection found")
            if not self.use_mock:
                threading.Timer(1, self._try_reconnect).start()

        if self.dashboard_ready is not None:
            if self.dashboard_ready.is_set():
                self.serialConnectedSender.send(self.serialConnected)
            else:
                threading.Thread(target=self._wait_for_dashboard_and_notify, daemon=True).start()

        super(processSerialHandler, self).run()

    # ===================================== PROCESS WORK ==========================================
    def process_work(self):
        serialConnectionStateMessage = self.serialConnectionStateSubscriber.receive()
        if serialConnectionStateMessage is False:
            self._handle_serial_disconnection()

    # ================================ STATE CHANGE HANDLER ========================================
    def state_change_handler(self):
        message = self.stateChangeSubscriber.receive()
        if message is not None:
            modeDict = SystemMode[message].value["serial_handler"]["process"]

            if modeDict["enabled"] == True:
                # only resume if serial is connected
                if self.serialConnected:
                    self.resume_threads()

            elif modeDict["enabled"] == False:
                self.pause_threads()

    # ===================================== STOP ==========================================
    def stop(self):
        """Stop the process."""
        # close serial connection
        if self.serialLock is not None:
            with self.serialLock:
                if self.serialCon:
                    try:
                        self.serialCon.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing serial port: {e}")
        else:
            if self.serialCon:
                try:
                    self.serialCon.close()
                except Exception as e:
                    self.logger.warning(f"Error closing serial port: {e}")

        super(processSerialHandler, self).stop()

    # ===================================== INIT TH =================================
    def _init_threads(self):
        """Initializes the read and the write thread."""
        readTh = threadRead(self, self.queuesList, self.debugging)
        writeTh = threadWrite(self, self.queuesList, self.debugging, self.example)
        self.threads.extend([readTh, writeTh])

        if not self.serialConnected:
            self.pause_threads()


# =================================== EXAMPLE =========================================
#             ++    THIS WILL RUN ONLY IF YOU RUN THE CODE FROM HERE  ++
#                  in terminal:    python3 processSerialHandler.py

if __name__ == "__main__":
    from multiprocessing import Queue, Pipe
    import time

    allProcesses = list()
    debugg = False
    # We have a list of multiprocessing.Queue() which individualy represent a priority for processes.
    queueList = {
        "Critical": Queue(),
        "Warning": Queue(),
        "General": Queue(),
        "Config": Queue(),
    }
    pipeRecv, pipeSend = Pipe(duplex=False)
    process = processSerialHandler(queueList, debugg, True)
    process.daemon = True
    process.start()
    time.sleep(4)  # modify the value to increase/decrease the time of the example
    process.stop()
