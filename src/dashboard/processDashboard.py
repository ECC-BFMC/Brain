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

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")


import psutil, json, logging, inspect, eventlet
from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from enum import Enum
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.templates.workerprocess import WorkerProcess
from src.utils.messages.allMessages import Semaphores
from src.dashboard.threads.threadStartFrontend import ThreadStartFrontend  
import src.utils.messages.allMessages as allMessages


class processDashboard(WorkerProcess):
    """This process handles the dashboard interactions, updating the UI based on the system's state.
    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
        deviceID (int): The identifier for the specific device.
    """
    # ====================================== INIT ==========================================
    def __init__(self, queueList, logging, debugging = False):
        super(processDashboard, self).__init__(queueList)
        self.running = True
        self.queueList = queueList
        self.logger = logging
        self.debugging = debugging

        self.messages = {}
        self.sendMessages = {}
        self.messagesAndVals = {}

        self.memoryUsage = 0
        self.cpuCoreUsage = 0
        self.cpuTemperature = 0

        self.sessionActive = False
        self.activeUser = None

        # setup Flask and SocketIO
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        CORS(self.app, supports_credentials=True)

        self.getNamesAndVals()
        self.messagesAndVals.pop("mainCamera", None)
        self.messagesAndVals.pop("Semaphores", None)
        self.subscribe()

        # define WebSocket event handlers
        self.socketio.on_event('message', self.handleMessage)
        self.socketio.on_event('save', self.handleSaveTableState)
        self.socketio.on_event('load', self.handleLoadTableState)

        # start hardware monitoring and continuous message sending
        self.sendContinuousHardwareData()
        eventlet.spawn(self.sendContinuousMessages)
        super(processDashboard, self).__init__(self.queueList)
        
    # ===================================== STOP ==========================================
    def stop(self):
        super(processDashboard, self).stop()
        self.running = False

    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializing methods and start the threads."""
        self._init_threads()
        for th in self.threads:
            th.daemon = self.daemon
            th.start()

        self.socketio.run(self.app, host='0.0.0.0', port=5005)

    def subscribe(self):
        """Subscribe function. In this function we make all the required subscribe to process gateway"""
        for name, enum in self.messagesAndVals.items():
            if enum["owner"] != "Dashboard":
                subscriber = messageHandlerSubscriber(self.queueList, enum["enum"], "lastOnly", True)
                self.messages[name] = {"obj": subscriber}
            else:
                sender = messageHandlerSender(self.queueList, enum["enum"])
                self.sendMessages[str(name)] = {"obj": sender}

        subscriber = messageHandlerSubscriber(self.queueList, Semaphores, "fifo", True)
        self.messages["Semaphores"] = {"obj": subscriber}

    def getNamesAndVals(self):
        """Extract all message names and values for processing."""
        classes = inspect.getmembers(allMessages, inspect.isclass)
        for name, cls in classes:
            if name != "Enum" and issubclass(cls, Enum):
                self.messagesAndVals[name] = {"enum": cls, "owner": cls.Owner.value}

    def sendMessageToBackend(self, dataName, dataDict):
        """Send messages to the backend."""
        if dataName in self.sendMessages:
            self.sendMessages[dataName]["obj"].send(dataDict.get("Value"))

    def handleMessage(self, data):
        """Handle incoming WebSocket messages."""
        if self.debugging:
            self.logger.info("Received message: " + str(data))

        dataDict = json.loads(data)
        dataName = dataDict["Name"]
        socketId = request.sid

        if dataName == "SessionAccess":
            self.handleSingleUserSession(socketId)
        elif dataName == "SessionEnd":
            self.handleSessionEnd(socketId)
        else:
            self.sendMessageToBackend(dataName, dataDict)

        emit('response', {'data': 'Message received: ' + str(data)}, room=socketId)

    def handleSingleUserSession(self, socketId):
        """Handle session access for a single user."""
        if not self.sessionActive:
            self.sessionActive = True
            self.activeUser = socketId
            self.socketio.emit('session_access', {'data': True}, room=socketId)
        elif self.activeUser == socketId:
            self.socketio.emit('session_access', {'data': True}, room=socketId)
        else:
            self.socketio.emit('session_access', {'data': False}, room=socketId)

    def handleSessionEnd(self, socketId):
        """Handle session end for the single user."""
        if self.sessionActive and self.activeUser == socketId:
            self.sessionActive = False
            self.activeUser = None

    def handleSaveTableState(self, data):
        """Handle saving the table state to a JSON file."""
        if self.debugging:
            self.logger.info("Received save message: " + data)

        dataDict = json.loads(data)
        file_path = '/home/pi/Brain/src/utils/table_state.json'  # change as necessary

        with open(file_path, 'w') as json_file:
            json.dump(dataDict, json_file, indent=4)

    def handleLoadTableState(self, data):
        """Handle loading the table state from a JSON file."""
        file_path = '/home/pi/Brain/src/utils/table_state.json'  # change as necessary

        try:
            with open(file_path, 'r') as json_file:
                dataDict = json.load(json_file)
            emit('loadBack', {'data': dataDict})
        except FileNotFoundError:
            emit('response', {'error': 'File not found. Please save the table state first.'})
        except json.JSONDecodeError:
            emit('response', {'error': 'Failed to parse JSON data from the file.'})

    def sendContinuousHardwareData(self):
        """Monitor and update hardware metrics periodically."""
        self.memoryUsage = psutil.virtual_memory().percent
        self.cpuCoreUsage = psutil.cpu_percent(interval=1, percpu=True)
        self.cpuTemperature = round(psutil.sensors_temperatures()['cpu_thermal'][0].current)
        eventlet.spawn_after(1, self.sendContinuousHardwareData)

    def sendContinuousMessages(self):
        """Send messages continuously to the frontend."""
        counter = 0
        socketSleep = 0.1
        sendTime = 1

        while self.running:
            for msg, subscriber in self.messages.items():
                resp = subscriber["obj"].receive()
                if resp is not None:
                    self.socketio.emit(msg, {"value": resp})
                    if self.debugging:
                        self.logger.info(f"{msg}: {resp}")

            if counter >= sendTime:
                self.socketio.emit('memory_channel', {'data': self.memoryUsage})
                self.socketio.emit('cpu_channel', {'data': {'usage': self.cpuCoreUsage, 'temp': self.cpuTemperature}})
                counter = 0
            else:
                counter += socketSleep

            eventlet.sleep(socketSleep)

    # ===================================== INIT TH ======================================
    def _init_threads(self):
        """Initialize the Dashboard thread."""
        dashboardThreadFrontend = ThreadStartFrontend(self.logger)
        self.threads.append(dashboardThreadFrontend)
