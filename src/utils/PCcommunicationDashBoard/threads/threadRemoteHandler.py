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
from src.templates.threadwithstop import ThreadWithStop
from src.utils.PCcommunicationDashBoard.threads.connection import FactoryDealer
from src.utils.PCcommunicationDashBoard.threads.periodics import PeriodicTask
from src.utils.messages.allMessages import (
    EnableButton,
    SignalRunning,
    Location,
    mainCamera,
    Signal,
)
from twisted.internet import reactor


class threadRemoteHandler(ThreadWithStop):
    """Thread which will handle processPCcommunicationDashboard functionalities. We will initailize a reactor with the factory class.

    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
        pipeRecv (multiprocessing.pipes.Pipe): The receiving pipe. This pipe will get the information from process gateway.
        pipeSend (multiprocessing.pipes.Pipe): The sending pipe. This pipe will be sent to process gateway as a way to send information.
    """

    # ===================================== INIT =====================================
    def __init__(self, queuesList, logging, pipeRecv, pipeSend):
        super(threadRemoteHandler, self).__init__()
        self.factory = FactoryDealer(queuesList)
        self.reactor = reactor
        self.reactor.listenTCP(5000, self.factory)
        self.queues = queuesList
        self.logging = logging
        self.pipeRecv = pipeRecv
        self.subscribe(pipeSend)
        self.task = PeriodicTask(
            self.factory, 0.001, self.pipeRecv
        )  # Replace X with the desired number of seconds

    def subscribe(self, pipeSend):
        """Subscribing function

        Args:
            pipeSend (multiprocessing.pipes.Pipe): The sending pipe
        """
        self.queues["Config"].put(
            {
                "Subscribe/Unsubscribe": "subscribe",
                "Owner": EnableButton.Owner.value,
                "msgID": EnableButton.msgID.value,
                "To": {"receiver": "threadRemoteHandler", "pipe": pipeSend},
            }
        )
        self.queues["Config"].put(
            {
                "Subscribe/Unsubscribe": "subscribe",
                "Owner": SignalRunning.Owner.value,
                "msgID": SignalRunning.msgID.value,
                "To": {"receiver": "threadRemoteHandler", "pipe": pipeSend},
            }
        )
        self.queues["Config"].put(
            {
                "Subscribe/Unsubscribe": "subscribe",
                "Owner": Location.Owner.value,
                "msgID": Location.msgID.value,
                "To": {"receiver": "threadRemoteHandler", "pipe": pipeSend},
            }
        )
        self.queues["Config"].put(
            {
                "Subscribe/Unsubscribe": "subscribe",
                "Owner": Signal.Owner.value,
                "msgID": Signal.msgID.value,
                "To": {"receiver": "threadRemoteHandler", "pipe": pipeSend},
            }
        )
        self.queues["Config"].put(
            {
                "Subscribe/Unsubscribe": "subscribe",
                "Owner": mainCamera.Owner.value,
                "msgID": mainCamera.msgID.value,
                "To": {"receiver": "threadRemoteHandler", "pipe": pipeSend},
            }
        )

    # ===================================== RUN ======================================
    def run(self):
        self.task.start()
        print("before run")
        self.reactor.run(installSignalHandlers=False)
        print("after run")

    # ==================================== STOP ======================================
    def stop(self):
        self.reactor.stop()
        super(threadRemoteHandler, self).stop()
