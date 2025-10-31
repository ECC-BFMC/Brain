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

import inspect
from multiprocessing import Pipe

class messageHandlerSubscriber: 
    """Class which will handle subscriber functionalities.\n
    Args:
        queuesList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
        message (enum): A specific message
        deliveryMode (string): Determines how messages are delivered from the queue. ("FIFO" or "LastOnly").
        subscribe (bool): A flag to automatically subscribe the message.
    """
        
    def __init__(self, queuesList, message, deliveryMode="fifo", subscribe=False):
        self._queuesList = queuesList
        self._message = message
        self._deliveryMode = str.lower(deliveryMode)
        self._pipeRecv, self._pipeSend = Pipe(duplex=False)
        frame = inspect.currentframe().f_back # type: ignore
        if 'self' in frame.f_locals: # type: ignore
            self._receiver = frame.f_locals['self'].__class__.__name__ # type: ignore
        else:
            self._receiver = frame.f_globals.get('__name__', None) # type: ignore
        
        if subscribe == True:
            self.subscribe()

        if self._deliveryMode not in ["fifo", "lastonly"]:
            print("WARNING! Wrong delivery mode supplied.", deliveryMode, "instead of FIFO or LastOnly.", self._message, self._receiver)
            print("WARNING! Switching to FIFO")
            self._deliveryMode = "fifo"

    def receive(self):
        """
        Receives values from a pipe

        Returns None if there no data in the Pipe
        """
        if not self._pipeRecv.poll():
            return None
        else:
            return self.receive_with_block()
        
    def receive_with_block(self):
        """
        Waits until there is an existing message in the pipe 
        
        Returns:
            message's data type: The received message.
        """
        
        message = self._pipeRecv.recv()
        messageType = type(message["value"]).__name__
        
        if self._deliveryMode == "fifo":
            if messageType != self._message.msgType.value:
                print("WARNING! Message type and value type are not matching.", self._message, "received:", messageType, "expected:", self._message.msgType.value)
            return message["value"]
        
        elif self._deliveryMode == "lastonly":
            while (self._pipeRecv.poll()):
                message = self._pipeRecv.recv()

            if messageType != self._message.msgType.value:
                print("WARNING! Message type and value type are not matching.", self._message, "received:", messageType, "expected:", self._message.msgType.value)
            return message["value"]
        
    def empty(self):
        """
        Empties the receiving pipe of any existing data.
        """
        while self._pipeRecv.poll():
            self._pipeRecv.recv()

    def subscribe(self):
        """
        Subscribes to messages.
        """
        self._queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": "subscribe",
                "Owner": self._message.Owner.value,
                "msgID": self._message.msgID.value,
                "To": {"receiver": self._receiver, "pipe": self._pipeSend},
            }
        )

    def unsubscribe(self):
        """
        Unsubscribes from messages.
        """
        self._queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": "unsubscribe",
                "Owner": self._message.Owner.value,
                "msgID": self._message.msgID.value,
                "To": {"receiver": self._receiver}
            }
        )

    def is_data_in_pipe(self):
        """
        Checks if there is any data in the receiving pipe.

        Returns:
            bool: True if data is available, False otherwise.
        """
        return self._pipeRecv.poll()

    def set_delivery_mode_to_fifo(self):
        """
        Sets delivery mode to FIFO.
        """
        self._deliveryMode = "fifo"

    def set_delivery_mode_to_last_only(self):
        """
        Sets delivery mode to LastOnly.
        """
        self._deliveryMode = "lastonly"

    def __del__(self): 
        """
        Cleans up by closing the pipes.
        """
        self._pipeRecv.close()
        self._pipeSend.close()
