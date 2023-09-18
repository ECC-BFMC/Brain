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
from twisted.internet import task
import json


class PeriodicTask(task.LoopingCall):
    """This period task will check if it is something to be send to Dashboard.

    Args:
        factory (protocol.Factory): This will handle what will happend tot he message to be send.
        interval (int): Time to redo the task.
        pipe (multiprocessing.pipes.Pipe): Pipe to receive information.
    """

    # ===================================== INIT ===========================================
    def __init__(self, factory, interval, pipe):
        super().__init__(self.periodicCheck)
        self.factory = factory
        self.interval = interval
        self.pipe = pipe

    # ===================================== START ==========================================
    def start(self):
        super().start(self.interval)

    # ===================================== STOP ===========================================
    def stop(self):
        if self.running:
            super().stop()

    # ================================= PERIOD CHECK =======================================
    def periodicCheck(self):
        """This function will check every interval of time if there is something to be send. If it is we will create the message and we will send it."""
        if self.pipe.poll():
            msg = self.pipe.recv()
            messageValue = msg["value"]
            messageType = msg["Type"]
            messageOwner = msg["Owner"]
            messageId = msg["id"]
            if not messageType == "base64":
                messageValue2 = json.dumps(messageValue)
                self.factory.send_data_to_client(
                    messageValue2, messageType, messageOwner, messageId
                )
            else:
                self.factory.send_data_to_client(
                    messageValue, messageType, messageOwner, messageId
                )
