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
import threading
from multiprocessing import Pipe
from src.hardware.serialhandler.threads.messageconverter import MessageConverter
from src.templates.threadwithstop import ThreadWithStop
from src.utils.messages.allMessages import (
    SignalRunning,
    EngineRun,
    Control,
    SteerMotor,
    SpeedMotor,
    Brake,
)


class threadWrite(ThreadWithStop):
    """This thread write the data that Raspberry PI send to NUCLEO.\n

    Args:
        queues (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
        serialCom (serial.Serial): Serial connection between the two boards.
        logFile (FileHandler): The path to the history file where you can find the logs from the connection.
        example (bool, optional): Flag for exmaple activation. Defaults to False.
    """

    # ===================================== INIT =========================================
    def __init__(self, queues, serialCom, logFile, example=False):
        super(threadWrite, self).__init__()
        self.queuesList = queues
        self.serialCom = serialCom
        self.logFile = logFile
        self.exampleFlag = example
        self.messageConverter = MessageConverter()
        self.running = False
        pipeRecvBreak, pipeSendBreak = Pipe(duplex=False)
        self.pipeRecvBreak = pipeRecvBreak
        self.pipeSendBreak = pipeSendBreak
        pipeRecvSpeed, pipeSendSpeed = Pipe(duplex=False)
        self.pipeRecvSpeed = pipeRecvSpeed
        self.pipeSendSpeed = pipeSendSpeed
        pipeRecvSteer, pipeSendSteer = Pipe(duplex=False)
        self.pipeRecvSteer = pipeRecvSteer
        self.pipeSendSteer = pipeSendSteer
        pipeRecvControl, pipeSendControl = Pipe(duplex=False)
        self.pipeRecvControl = pipeRecvControl
        self.pipeSendControl = pipeSendControl
        pipeRecvRunningSignal, pipeSendRunningSignal = Pipe(duplex=False)
        self.pipeRecvRunningSignal = pipeRecvRunningSignal
        self.pipeSendRunningSignal = pipeSendRunningSignal
        self.subscribe()
        self.Queue_Sending()
        if example:
            self.i = 0.0
            self.j = -1.0
            self.s = 0.0
            self.example()

    def subscribe(self):
        """Subscribe function. In this function we make all the required subscribe to process gateway"""
        self.queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": 1,
                "Owner": EngineRun.Owner.value,
                "msgID": EngineRun.msgID.value,
                "To": {
                    "receiver": "threadWrite",
                    "pipe": self.pipeSendRunningSignal,
                },
            }
        )
        self.queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": 1,
                "Owner": Control.Owner.value,
                "msgID": Control.msgID.value,
                "To": {
                    "receiver": "threadWrite",
                    "pipe": self.pipeSendControl,
                },
            }
        )
        self.queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": 1,
                "Owner": SteerMotor.Owner.value,
                "msgID": SteerMotor.msgID.value,
                "To": {"receiver": "threadWrite", "pipe": self.pipeSendSteer},
            }
        )
        self.queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": 1,
                "Owner": SpeedMotor.Owner.value,
                "msgID": SpeedMotor.msgID.value,
                "To": {"receiver": "threadWrite", "pipe": self.pipeSendSpeed},
            }
        )
        self.queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": 1,
                "Owner": Brake.Owner.value,
                "msgID": Brake.msgID.value,
                "To": {"receiver": "threadWrite", "pipe": self.pipeSendBreak},
            }
        )

    # ==================================== SENDING =======================================
    def Queue_Sending(self):
        """Callback function for engine running flag."""
        self.queuesList["General"].put(
            {
                "Owner": SignalRunning.Owner.value,
                "msgID": SignalRunning.msgID.value,
                "msgType": SignalRunning.msgType.value,
                "msgValue": self.running,
            }
        )
        threading.Timer(1, self.Queue_Sending).start()

    # ===================================== RUN ==========================================
    def run(self):
        """In this function we check if we got the enable engine signal. After we got it we will start getting messages from raspberry PI. It will transform them into NUCLEO commands and send them."""
        while self._running:
            try:
                if self.pipeRecvRunningSignal.poll():
                    msg = self.pipeRecvRunningSignal.recv()
                    if msg["value"] == True:
                        self.running = True
                    else:
                        self.running = False
                        command = {"action": "1", "speed": 0.0}
                        command_msg = self.messageConverter.get_command(**command)
                        self.serialCom.write(command_msg.encode("ascii"))
                        self.logFile.write(command_msg)
                        command = {"action": "2", "steerAngle": 0.0}
                        command_msg = self.messageConverter.get_command(**command)
                        self.serialCom.write(command_msg.encode("ascii"))
                        self.logFile.write(command_msg)
                if self.running:
                    if self.pipeRecvBreak.poll():
                        message = self.pipeRecvBreak.recv()
                        command = {"action": "1", "speed": float(message["value"])}
                        command_msg = self.messageConverter.get_command(**command)
                        self.serialCom.write(command_msg.encode("ascii"))
                        self.logFile.write(command_msg)
                    elif self.pipeRecvSpeed.poll():
                        message = self.pipeRecvSpeed.recv()
                        command = {"action": "1", "speed": float(message["value"])}
                        command_msg = self.messageConverter.get_command(**command)
                        self.serialCom.write(command_msg.encode("ascii"))
                        self.logFile.write(command_msg)
                    elif self.pipeRecvSteer.poll():
                        message = self.pipeRecvSteer.recv()
                        command = {"action": "2", "steerAngle": float(message["value"])}
                        command_msg = self.messageConverter.get_command(**command)
                        self.serialCom.write(command_msg.encode("ascii"))
                        self.logFile.write(command_msg)
            except Exception as e:
                print(e)

    # ==================================== START =========================================
    def start(self):
        super(threadWrite, self).start()

    # ==================================== STOP ==========================================
    def stop(self):
        """This function will close the thread and will stop the car."""
        import time

        self.exampleFlag = False
        self.pipeSendSteer.send({"Type": "Steer", "value": 0.0})
        self.pipeSendSpeed.send({"Type": "Speed", "value": 0.0})
        time.sleep(2)
        super(threadWrite, self).stop()

    # ================================== EXAMPLE =========================================
    def example(self):
        """This function simulte the movement of the car."""
        if self.exampleFlag:
            self.pipeSendRunningSignal.send({"Type": "Run", "value": True})
            self.pipeSendSpeed.send({"Type": "Speed", "value": self.s})
            self.pipeSendSteer.send({"Type": "Steer", "value": self.i})
            self.i += self.j
            if self.i >= 21.0:
                self.i = 21.0
                self.s = self.i / 7
                self.j *= -1
            if self.i <= -21.0:
                self.i = -21.0
                self.s = self.i / 7
                self.j *= -1.0
            threading.Timer(0.01, self.example).start()
