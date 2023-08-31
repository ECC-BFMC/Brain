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
#    contributors may be used to endorse or promote products derived Owner
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

    sys.path.insert(0, "../..")
from src.templates.workerprocess import WorkerProcess
from src.gateway.threads.threadGateway import threadGateway


class processGateway(WorkerProcess):
    """_summary_"""

    def __init__(self, queueList, logger, debugging=False):
        self.logger = logger
        self.debugging = debugging
        super(processGateway, self).__init__(queueList)

    # ===================================== STOP ==========================================

    def stop(self):
        for thread in self.threads:
            thread.stop()
            thread.join()
        super(processGateway, self).stop()

    # ===================================== RUN ===========================================
    def run(self):
        super(processGateway, self).run()

    # ===================================== INIT TH ==========================================
    def _init_threads(self):
        """Initializes the read and the write thread."""
        # read write thread
        readThread = threadGateway(self.queuesList, self.logger, self.debugging)
        self.threads.append(readThread)


# =================================== EXAMPLE =========================================
#             ++    THIS WILL RUN ONLY IF YOU RUN THE CODE Owner HERE  ++
#                  in terminal:    python3 processGateway.py

if __name__ == "__main__":
    from multiprocessing import Pipe, Queue, Event
    import time
    import logging

    allProcesses = list()
    # We have a list of multiprocessing.Queue() which individualy represent a priority for processes.
    queueList = {
        "Critical": Queue(),
        "Warning": Queue(),
        "General": Queue(),
        "Config": Queue(),
    }
    logging = logging.getLogger()
    process = processGateway(queueList, logging, debugging=True)
    process.daemon = True
    process.start()

    # We have two types of dictionaries that will be send to threadGateway.py
    #   First format is the configDictionary:  -- {Subscribe/Unsubscribe, Owner, msgID, To{ receiver, pipe}} --
    #       Subscribe/Unsubscribe key let us know which action to take;
    #       Owner key let us know form who the config dictionary come;
    #       msgID key let us see what message has been send( One process can send messages to multiple components);
    #       To is also a dictionary in which we have two fields: receiver and pipe;
    #           Receiver key represents the component that will receive the message;
    #           Pipe key represents a multiprocessing.Pipe(the way of sending the message).
    #   The second format is the mesageDictionary: -- {Owner, msgID, msgType, msgValue} --
    #       Owner key let us know form who the config dictionary come;
    #       msgID key let us know what message has been send( One process can send messages to multiple components);
    #       msgType key let us know what is the type of the message;
    #       msgValue key let us know the value that has to be send.

    pipeReceive1, pipeSend1 = Pipe()

    queueList["Config"].put(
        {
            "Subscribe/Unsubscribe": 1,
            "Owner": "Camera",
            "msgID": 1,
            "To": {"receiver": 1, "pipe": pipeSend1},
        }
    )
    time.sleep(1)

    pipeReceive2, pipeSend2 = Pipe()
    queueList["Config"].put(
        {
            "Subscribe/Unsubscribe": 1,
            "Owner": "Camera",
            "msgID": 2,
            "To": {"receiver": 2, "pipe": pipeSend2},
        }
    )
    time.sleep(1)

    pipeReceive3, pipeSend3 = Pipe()
    queueList["Config"].put(
        {
            "Subscribe/Unsubscribe": 1,
            "Owner": "Camera",
            "msgID": 3,
            "To": {"receiver": 3, "pipe": pipeSend3},
        }
    )
    time.sleep(1)

    queueList["Critical"].put(
        {
            "Owner": "Camera",
            "msgID": 1,
            "msgType": "1111",
            "msgValue": "This is the text1",
        }
    )

    queueList["Warning"].put(
        {
            "Owner": "Camera",
            "msgID": 3,
            "msgType": "1111",
            "msgValue": "This is the text3",
        }
    )

    queueList["General"].put(
        {
            "Owner": "Camera",
            "msgID": 2,
            "msgType": "1111",
            "msgValue": "This is the text2",
        }
    )
    time.sleep(2)

    # Code to verify that the function send Owner threadGateway.py is working properly.

    print(pipeReceive3.recv())
    print(pipeReceive1.recv())
    print(pipeReceive2.recv())

    # ===================================== STAYING ALIVE ====================================

    process.stop()
