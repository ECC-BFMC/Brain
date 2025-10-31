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
import logging
import time
import threading
import re
import os
import serial
from datetime import datetime, timedelta

from src.templates.threadwithstop import ThreadWithStop
from src.utils.messages.allMessages import (
    BatteryLvl,
    ImuData,
    ImuAck,
    InstantConsumption,
    EnableButton,
    ResourceMonitor,
    CurrentSpeed,
    CurrentSteer,
    ShutDownSignal,
    SerialConnectionState,
    CalibPWMData,
    CalibRunDone,
    SteeringLimits,
    AliveSignal
)
from src.utils.messages.messageHandlerSender import messageHandlerSender


class threadRead(ThreadWithStop):
    """This thread read the data that NUCLEO send to Raspberry PI.\n

    Args:
        process (processSerialHandler): ProcessSerialHandler object.
        logFile (FileHandler): The path to the history file where you can find the logs from the connection.
        queueList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
    """

    # ===================================== INIT =========================================
    def __init__(self, process, logFile, queueList, logger, debugger = False):
        super(threadRead, self).__init__(pause=0.01)
        self.process = process
        self.logFile = logFile
        self.buffer = ""
        self.queuesList = queueList
        self.logger = logger
        self.debugger = debugger
        self.event = threading.Event()
        self._init_senders()

        self.expectedValues = {"kl": "0, 15 or 30", "instant": "1 or 0", "battery": "1 or 0",
                               "resourceMonitor": "1 or 0", "imu": "1 or 0", "steer" : "between -25 and 25",
                               "speed": "between -500 and 500", "break": "between -250 and 250"}

        self.warningPattern = r'^(-?[0-9]+)H(-?[0-5]?[0-9])M(-?[0-5]?[0-9])S$'
        self.resourceMonitorPattern = r'Heap \((\d+\.\d+)\);Stack \((\d+\.\d+)\)'

        # error rate limiting
        self.last_error_time = None
        self.error_cooldown = timedelta(seconds=3)

        self.queue_sending()

    def _init_senders(self):
        self.enableButtonSender = messageHandlerSender(self.queuesList, EnableButton)
        self.batteryLvlSender = messageHandlerSender(self.queuesList, BatteryLvl)
        self.instantConsumptionSender = messageHandlerSender(self.queuesList, InstantConsumption)
        self.imuDataSender = messageHandlerSender(self.queuesList, ImuData)
        self.imuAckSender = messageHandlerSender(self.queuesList, ImuAck)
        self.resourceMonitorSender = messageHandlerSender(self.queuesList, ResourceMonitor)
        self.currentSpeedSender = messageHandlerSender(self.queuesList, CurrentSpeed)
        self.currentSteerSender = messageHandlerSender(self.queuesList, CurrentSteer)
        self.warningSender = messageHandlerSender(self.queuesList, ShutDownSignal)
        self.serialConnectionStateSender = messageHandlerSender(self.queuesList, SerialConnectionState)
        self.calibPWMDataSender = messageHandlerSender(self.queuesList, CalibPWMData)
        self.calibRunDoneSender = messageHandlerSender(self.queuesList, CalibRunDone)
        self.steeringLimitsSender = messageHandlerSender(self.queuesList, SteeringLimits)
        self.aliveSignalSender = messageHandlerSender(self.queuesList, AliveSignal)

    # ====================================== RUN ==========================================
    def thread_work(self):
        try:
            with self.process.serialLock:
                serial_con = self.process.serialCon
                if serial_con is None or not self.process.serialConnected or not serial_con.is_open:
                    return

                if serial_con.in_waiting > 0:
                    try:
                        data = serial_con.read(serial_con.in_waiting).decode("ascii")
                        self.buffer += data

                    except Exception as e:
                        if self._should_send_error():
                            self.serialConnectionStateSender.send(False)
                            print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;91mERROR\033[0m - Reading from serial ({e})")
                        return

            while ";;" in self.buffer:
                msg, self.buffer = self.buffer.split(";;", 1)

                if msg.strip():
                    try:
                        self.send_queue(msg.strip())
                    except Exception as e:
                        print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;91mERROR\033[0m - Processing message \033[94m{msg.strip()}\033[0m ({e})")

        except Exception as e:
            if self._should_send_error():
                self.serialConnectionStateSender.send(False)
                print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;91mERROR\033[0m - Thread run method ({e})")

    # ==================================== SENDING =======================================
    def queue_sending(self):
        """Callback function for enable button flag."""
        self.enableButtonSender.send(True)
        threading.Timer(1, self.queue_sending).start()

    def send_queue(self, buff):
        """This function select which type of message we receive from NUCLEO and send the data further."""

        if '@' in buff and ':' in buff:
            action, value = buff.split(":") 
            action = action[1:]
            if self.debugger:
                self.logger.info(buff)

            if action == "imu":
                splittedValue = value.split(";")
                if(len(buff)>20):
                    data = {
                        "roll": splittedValue[0],
                        "pitch": splittedValue[1],
                        "yaw": splittedValue[2],
                        "accelx": splittedValue[3],
                        "accely": splittedValue[4],
                        "accelz": splittedValue[5],
                    }
                    self.imuDataSender.send(str(data))
                else:
                    self.imuAckSender.send(splittedValue[0])

            elif action == "brake":
                self.currentSpeedSender.send(0.0)
                self.currentSteerSender.send(0.0)

            elif action == "speed":
                speed = value.split(",")[0]
                if (lambda v: (lambda: float(v), True)[1] if isinstance(v, str) else False)(speed):
                    self.currentSpeedSender.send(float(speed))

            elif action == "steer":
                steer = value.split(",")[0]
                if (lambda v: (lambda: float(v), True)[1] if isinstance(v, str) else False)(steer):
                    self.currentSteerSender.send(float(steer))

            elif action == "vcdCalib":
                splittedValue = value.split(";")
                speedPWM = splittedValue[0]
                steerPWM = splittedValue[1]
                
                if speedPWM == "0" and steerPWM == "0":
                    self.calibRunDoneSender.send(True)
                else:
                    self.calibPWMDataSender.send({"speedPWM": speedPWM, "steerPWM": steerPWM})

            elif action == "alive":
                self.aliveSignalSender.send(True)

            elif action == "steerLimits":
                splittedValue = value.split(";")
                lowerLimit = splittedValue[0]
                upperLimit = splittedValue[1]
                self.steeringLimitsSender.send({"lowerLimit": lowerLimit, "upperLimit": upperLimit})
                
            elif action == "instant":
                if self.check_valid_value(action, value):
                    self.instantConsumptionSender.send(float(value))

            elif action == "battery":
                if self.check_valid_value(action, value):
                    percentage = (int(value)-7000)/14
                    percentage = max(0, min(100, round(percentage)))

                    self.batteryLvlSender.send(percentage)

            elif action == "resourceMonitor":
                if self.check_valid_value(action, value):
                    data = re.match(self.resourceMonitorPattern, value)
                    if data:
                        message = {"heap": data.group(1), "stack": data.group(2)}
                        self.resourceMonitorSender.send(message)

            elif action == "warning":
                data = re.match(self.warningPattern, value)
                if data:
                    print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;93mWARNING\033[0m - Shutdown in \033[94m{data.group(1)}h {data.group(2)}m {data.group(3)}s\033[0m")
                    self.warningSender.send(data)
                    
            elif action == "shutdown":
                print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;93mWARNING\033[0m - \033[94mShutting down now!\033[0m")
                self.event.wait(3)
                os.system("sudo shutdown -h now")
            
    def check_valid_value(self, action, message):
        if message == "syntax error":
            print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;93mWARNING\033[0m - Invalid \033[94m{action.upper()}\033[0m value (expected {self.expectedValues[action]})")
            return False
    
        if message == "kl 15/30 is required!!":
            print(f"\033[1;97m[ Serial Handler ] :\033[0m \033[1;93mWARNING\033[0m - KL 15/30 required for \033[94m{action.upper()}\033[0m")
            return False
        
        if message == "ack":
            return False
        return True
    
    def is_float(self, string):
        try:
            float(string)
        except ValueError:
            return False

        return True

    def _should_send_error(self):
        """Check if we should send an error message (rate limiting)."""
        now = datetime.now()
        if self.last_error_time is None or (now - self.last_error_time) >= self.error_cooldown:
            self.last_error_time = now
            return True
        return False