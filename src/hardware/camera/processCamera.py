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

from src.templates.workerprocess import WorkerProcess
from src.hardware.camera.threads.threadCamera import threadCamera
from src.statemachine.stateMachine import StateMachine
from src.statemachine.systemMode import SystemMode
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.allMessages import StateChange


class processCamera(WorkerProcess):
    """This process handle camera.\n
    Args:
            queueList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
            debugging (bool, optional): A flag for debugging. Defaults to False.
    """

    # ====================================== INIT ==========================================
    def __init__(self, queueList, ready_event=None, debugging=False, dev_mode=False):
        self.queuesList = queueList
        self.debugging = debugging
        self.dev_mode = dev_mode
        self.stateChangeSubscriber = messageHandlerSubscriber(self.queuesList, StateChange, "lastOnly", True)

        super(processCamera, self).__init__(self.queuesList, ready_event)

    # ================================ STATE CHANGE HANDLER ========================================
    def state_change_handler(self):
        message = self.stateChangeSubscriber.receive()
        if message is not None:
            modeDict = SystemMode[message].value["camera"]["process"]

            if modeDict["enabled"] == True:
                self.resume_threads()
            elif modeDict["enabled"] == False:
                self.pause_threads()

    # ===================================== INIT TH ======================================
    def _init_threads(self):
        """Create the Camera Publisher thread and add to the list of threads."""
        camTh = threadCamera(self.queuesList, self.debugging, self.dev_mode)
        self.threads.append(camTh)


# =================================== EXAMPLE =========================================
#             ++    THIS WILL RUN ONLY IF YOU RUN THE CODE FROM HERE  ++
#                  in terminal:    python3 processCamera.py
if __name__ == "__main__":
    from multiprocessing import Queue
    import time
    import cv2

    from src.gateway.processGateway import processGateway
    from src.utils.messages.allMessages import serialCamera
    from src.utils.sharedFrameBuffer import NotifiedFrameReader

    debugg = True

    queueList = {
        "Critical": Queue(),
        "Warning": Queue(),
        "General": Queue(),
        "Config": Queue(),
    }

    # the gateway is needed: it routes the frame notifications and tells the
    # camera that someone subscribed (otherwise no stream is produced)
    gateway = processGateway(queueList)
    gateway.start()

    subscriber = messageHandlerSubscriber(queueList, serialCamera, "lastOnly", True)

    process = processCamera(queueList, debugg)
    process.daemon = True
    process.start()

    if debugg:
        print("getting")
    frameReader = NotifiedFrameReader()
    result = None
    deadline = time.time() + 10
    while result is None and time.time() < deadline:
        notification = subscriber.receive()
        if notification is not None:
            result = frameReader.read(notification)
        time.sleep(0.05)
    if result is None:
        raise TimeoutError("No camera frame received")

    frame, timestamp, seq = result
    if debugg:
        print(f"got frame {seq} at {timestamp}")
    cv2.imwrite("test.jpg", frame)
    frameReader.close()

    process.stop()
    gateway.stop()
