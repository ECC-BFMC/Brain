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
# import eventlet
# eventlet.monkey_patch()

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")

import inspect, psutil, json, threading

from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from enum import Enum
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.templates.workerprocess import WorkerProcess
from src.dashboard.threads.threadStartFrontend import ThreadStartFrontend  
from src.utils.messages.allMessages import Semaphores
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

        self.running = True
        self.queueList = queueList
        self.logger = logging
        self.debugging = debugging
        self.messages = {}
        self.sendMessages = {}
        self.messagesAndVals = {}
        self.memory_usage = 0
        self.cpu_core_usage = 0
        self.cpu_temperature = 0
        
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*",async_mode='eventlet')
        CORS(self.app, supports_credentials=True)

        self.getNamesAndVals()
        # Remove the mainCamera and Semaphores message sender
        self.messagesAndVals.pop("mainCamera")
        self.messagesAndVals.pop("Semaphores")

        self.subscribe()

        # Define WebSocket event handlers
        self.socketio.on_event('message', self.handle_message)
        self.socketio.on_event('save', self.handle_saveTableState)
        self.socketio.on_event('load', self.handle_loadTableState)

        # Setting up a background task to automatically send the information to the host
        self.send_continuous_hardware_data()
        self.socketio.start_background_task(self.send_continuous_messages)
        super(processDashboard, self).__init__(self.queueList)

    # ===================================== STOP ==========================================
    def stop(self):
        super(processDashboard, self).stop()

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
                sender = messageHandlerSender(self.queueList,enum["enum"])
                self.sendMessages[str(name)] = {"obj": sender}
        subscriber = messageHandlerSubscriber(self.queueList, Semaphores, "fifo", True) # we need it as a fifo so we can see all the semaphores status
        self.messages["Semaphores"] = {"obj": subscriber}
                
    def getNamesAndVals(self):
        classes = inspect.getmembers(allMessages, inspect.isclass)
        for name, cls in classes:
            if name != "Enum" and issubclass(cls, Enum):
                self.messagesAndVals[name] = {"enum": cls, "owner": cls.Owner.value}

    def handle_message(self, data):
        if self.debugging:
            self.logger.info("Received message: " + str(data))
        dataDict= json.loads(data)
        self.sendMessages[dataDict["Name"]]["obj"].send(dataDict["Value"])
        emit('response', {'data': 'Message received: ' + str(data)})

    def handle_saveTableState(self, data):
        if self.debugging:
            self.logger.info("Received message: " + data)
        dataDict = json.loads(data)
        with open('/home/pi/Brain/src/utils/table_state.json', 'w') as json_file: # change me(path) 
            json.dump(dataDict, json_file, indent=4)  

    def handle_loadTableState(self, data):
        file_path = '/home/pi/Brain/src/utils/table_state.json' # change me(path)
        
        try:
            with open(file_path, 'r') as json_file:
                dataDict = json.load(json_file) 
            emit('loadBack', {'data': dataDict})
        except FileNotFoundError:
            emit('response', {'error': 'File not found. Please save the table state first.'})
        except json.JSONDecodeError:
            emit('response', {'error': 'Failed to parse JSON data from the file.'})

    def send_continuous_hardware_data(self):   
        self.memory_usage = psutil.virtual_memory().percent
        self.cpu_core_usage = psutil.cpu_percent(interval=1, percpu=True)
        self.cpu_temperature = round(psutil.sensors_temperatures()['cpu_thermal'][0].current)
        threading.Timer(1, self.send_continuous_hardware_data).start()

    def send_continuous_messages(self):
        counter = 1   
        socketSleep = 0.025
        sendTime = 1 
        while self.running == True:
            for msg in self.messages:
                resp = self.messages[msg]["obj"].receive()
                if resp is not None:
                    self.socketio.emit(msg, {"value": resp})
                    if self.debugging:
                        self.logger.info(str(msg))
                        self.logger.info(str(resp))
            if counter < sendTime:
                counter += socketSleep
            else:
                self.socketio.emit('memory_channel', {'data': self.memory_usage})
                self.socketio.emit('cpu_channel', {'data': {'usage': self.cpu_core_usage, 'temp': self.cpu_temperature}})
                counter = 0
            self.socketio.sleep(socketSleep)

    # ===================================== INIT TH ======================================
    def _init_threads(self):
        """Create the Dashboard thread and add to the list of threads."""
        dashboardThreadFrontend = ThreadStartFrontend(self.logger)
        self.threads.append(dashboardThreadFrontend)
