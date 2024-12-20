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

import time
import threading
import re
import os

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
    WarningSignal
)
from src.utils.messages.messageHandlerSender import messageHandlerSender


class threadRead(ThreadWithStop):
    """This thread read the data that NUCLEO send to Raspberry PI.\n

    Args:
        f_serialCon (serial.Serial): Serial connection between the two boards.
        f_logFile (FileHandler): The path to the history file where you can find the logs from the connection.
        queueList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
    """

    # ===================================== INIT =========================================
    def __init__(self, f_serialCon, f_logFile, queueList, logger, debugger = False):
        self.serialCon = f_serialCon
        self.logFile = f_logFile
        self.buff = ""
        self.isResponse = False
        self.queuesList = queueList
        self.acumulator = 0
        self.logger = logger
        self.debugger = debugger
        self.currentSpeed = 0
        self.currentSteering = 0

        self.enableButtonSender = messageHandlerSender(self.queuesList, EnableButton)
        self.batteryLvlSender = messageHandlerSender(self.queuesList, BatteryLvl)
        self.instantConsumptionSender = messageHandlerSender(self.queuesList, InstantConsumption)
        self.imuDataSender = messageHandlerSender(self.queuesList, ImuData)
        self.imuAckSender = messageHandlerSender(self.queuesList, ImuAck)
        self.resourceMonitorSender = messageHandlerSender(self.queuesList, ResourceMonitor)
        self.currentSpeedSender = messageHandlerSender(self.queuesList, CurrentSpeed)
        self.currentSteerSender = messageHandlerSender(self.queuesList, CurrentSteer)
        self.warningSender = messageHandlerSender(self.queuesList, WarningSignal)

        self.expectedValues = {"kl": "0, 15 or 30", "instant": "1 or 0", "battery": "1 or 0",
                               "resourceMonitor": "1 or 0", "imu": "1 or 0", "steer" : "between -25 and 25", 
                               "speed": "between -500 and 500", "break": "between -250 and 250"}
        
        self.warningPattern = r'^(-?[0-9]+)H(-?[0-5]?[0-9])M(-?[0-5]?[0-9])S$'
        self.resourceMonitorPattern = r'Heap \((\d+\.\d+)\);Stack \((\d+\.\d+)\)'

        self.Queue_Sending()
        
        super(threadRead, self).__init__()

    # ====================================== RUN ==========================================
    def run(self):
        while self._running:
            # read_chr = self.serialCon.read()

            if self.serialCon.in_waiting > 0:
                try:
                    self.buff = self.serialCon.readline().decode("ascii")
                    self.sendqueue(self.buff)
                except Exception as e:
                    print("ThreadRead -> run method:", e)
            
            # try:
            #     read_chr = read_chr.decode("ascii")
            #     if read_chr == "@":
            #         self.isResponse = True
            #         self.buff = ""
            #     elif read_chr == "\r":
            #         self.isResponse = False
            #         if len(self.buff) != 0:
            #             self.sendqueue(self.buff)
            #     if self.isResponse:
            #         self.buff += read_chr
            # except Exception as e :
            #     print(e)

    # ==================================== SENDING =======================================
    def Queue_Sending(self):
        """Callback function for enable button flag."""
        self.enableButtonSender.send(True)
        threading.Timer(1, self.Queue_Sending).start()

    def sendqueue(self, buff):
        """This function select which type of message we receive from NUCLEO and send the data further."""

        if '@' in buff and ':' in buff:
            action, value = buff.split(":") # @action:value;;
            action = action[1:]
            value = value[:-4]

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

            elif action == "speed":
                speed = value.split(",")[0]
                if (lambda v: (lambda: float(v), True)[1] if isinstance(v, str) else False)(speed):
                    self.currentSpeedSender.send(float(speed))

            elif action == "steer":
                steer = value.split(",")[0]
                if (lambda v: (lambda: float(v), True)[1] if isinstance(v, str) else False)(steer):
                    self.currentSteerSender.send(float(steer))

            elif action == "instant":
                if self.checkValidValue(action, value):
                    self.instantConsumptionSender.send(float(value)/1000.0)

            elif action == "battery":
                if self.checkValidValue(action, value):
                    percentage = (int(value)-7200)/12
                    percentage = max(0, min(100, round(percentage)))

                    self.batteryLvlSender.send(percentage)

            elif action == "resourceMonitor":
                if self.checkValidValue(action, value):
                    data = re.match(self.resourceMonitorPattern, value)
                    if data:
                        message = {"heap": data.group(1), "stack": data.group(2)}
                        self.resourceMonitorSender.send(message)

            elif action == "warning":
                data = re.match(self.warningPattern, value)
                if data:
                    print(f"WARNING! Shutting down in {data.group(1)} hours {data.group(2)} minutes {data.group(3)} seconds")
                    self.warningSender.send(action,data)
                    
            elif action == "shutdown":
                print("SHUTTING DOWN!")
                time.sleep(3)
                os.system("sudo shutdown -h now")
            
    def checkValidValue(self, action, message):
        if message == "syntax error":
            print(f"WARNING! Invalid value for {action.upper()} (expected {self.expectedValues[action]})")
            return False
    
        if message == "kl 15/30 is required!!":
            print(f"WARNING! KL set to 15 or 30 is required to perform {action.upper()} action")
            return False
        
        if message == "ack":
            return False
        return True
    
    def isFloat(self, string):
        try: 
            float(string)
        except ValueError:
            return False
        
        return True