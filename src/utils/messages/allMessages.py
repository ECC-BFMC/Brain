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
from enum import Enum


####################################### processCamera #######################################
class mainCamera(Enum):
    Queue = "General"
    Owner = "processCamera"
    msgID = 1
    msgType = "base64"


class serialCamera(Enum):
    Queue = "General"
    Owner = "processCamera"
    msgID = 2
    msgType = "base64"


class Recording(Enum):
    Queue = "General"
    Owner = "processCamera"
    msgID = 3
    msgType = "Boolean3"


class Signal(Enum):
    Queue = "General"
    Owner = "processCamera"
    msgID = 4
    msgType = "String"


################################# processCarsAndSemaphores ##################################
class Cars(Enum):
    Queue = "General"
    Owner = "processCarsAndSemaphores"
    msgID = 1
    msgType = "Position"


class Semaphores(Enum):
    Queue = "General"
    Owner = "processCarsAndSemaphores"
    msgID = 2
    msgType = "State&Position"


################################# From PC ##################################
class EngineRun(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 1
    msgType = "EngineFlag"


class SpeedMotor(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 2
    msgType = "Speed"


class SteerMotor(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 3
    msgType = "SteerAngle"


class Control(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 4
    msgType = "Tasks"


class Brake(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 5
    msgType = "Speed"


class Record(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 6
    msgType = "Record"


class Config(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 7
    msgType = "Dict"


################################# From Nucleo ##################################
class BatteryLvl(Enum):
    Queue = "General"
    Owner = "threadReadSerial"
    msgID = 1
    msgType = "BatteryLVL"


class ImuData(Enum):
    Queue = "General"
    Owner = "threadReadSerial"
    msgID = 2
    msgType = "IMUData"


class InstantConsumption(Enum):
    Queue = "General"
    Owner = "threadReadSerial"
    msgID = 3
    msgType = "Consumption"


################################# From Locsys ##################################
class Location(Enum):
    Queue = "General"
    Owner = "tcpLocsys"
    msgID = 1
    msgType = "dict"


######################    From processSerialHandler  ###########################
class EnableButton(Enum):
    Queue = "General"
    Owner = "processSerialHandler"
    msgID = 1
    msgType = "Boolean"


class SignalRunning(Enum):
    Queue = "General"
    Owner = "processSerialHandler"
    msgID = 2
    msgType = "Boolean2"
