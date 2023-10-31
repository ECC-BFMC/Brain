# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC orginazers
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
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ===================================== GENERAL IMPORTS ==================================
import sys

sys.path.append(".")
from multiprocessing import Queue, Event
import logging


# ===================================== PROCESS IMPORTS ==================================
from src.gateway.processGateway import processGateway
from src.hardware.camera.processCamera import processCamera
from src.hardware.serialhandler.processSerialHandler import processSerialHandler
from src.utils.PCcommunicationDemo.processPCcommunication import (
    processPCCommunicationDemo,
)
from src.utils.PCcommunicationDashBoard.processPCcommunication import (
    processPCCommunicationDashBoard,
)
from src.data.CarsAndSemaphores.processCarsAndSemaphores import processCarsAndSemaphores
from src.data.TrafficCommunication.processTrafficCommunication import (
    processTrafficCommunication,
)

# ======================================== SETTING UP ====================================
allProcesses = list()
queueList = {
    "Critical": Queue(),
    "Warning": Queue(),
    "General": Queue(),
    "Config": Queue(),
}

logging = logging.getLogger()

TrafficCommunication = True
Camera = True
PCCommunicationDemo = True
CarsAndSemaphores = True
SerialHandler = True
# ===================================== SETUP PROCESSES ==================================

# Initializing gateway
processGateway = processGateway(queueList, logging)
allProcesses.append(processGateway)

# Initializing camera
if Camera:
    processCamera = processCamera(queueList, logging)
    allProcesses.append(processCamera)

# Initializing interface
if PCCommunicationDemo:
    processPCCommunication = processPCCommunicationDemo(queueList, logging)
    allProcesses.append(processPCCommunication)
else:
    processPCCommunicationDashBoard = processPCCommunicationDashBoard(
        queueList, logging
    )
    allProcesses.append(processPCCommunicationDashBoard)

# Initializing cars&sems
if CarsAndSemaphores:
    processCarsAndSemaphores = processCarsAndSemaphores(queueList)
    allProcesses.append(processCarsAndSemaphores)

# Initializing GPS
if TrafficCommunication:
    processTrafficCommunication = processTrafficCommunication(queueList, logging, 3)
    allProcesses.append(processTrafficCommunication)

# Initializing serial connection NUCLEO - > PI
if SerialHandler:
    processSerialHandler = processSerialHandler(queueList, logging)
    allProcesses.append(processSerialHandler)

# ===================================== START PROCESSES ==================================
for process in allProcesses:
    process.daemon = True
    process.start()

# ===================================== STAYING ALIVE ====================================
blocker = Event()
try:
    blocker.wait()
except KeyboardInterrupt:
    print("\nCatching a KeyboardInterruption exception! Shutdown all processes.\n")
    for proc in allProcesses:
        print("Process stopped", proc)
        proc.stop()
        proc.join()
