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

from multiprocessing import Pipe


class messageHandlerSender:
    """Class which will handle sender functionalities.\n
    Args:
        queuesList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        message (enum): A specific message
    """

    def __init__(self, queuesList, message):
        self.queuesList = queuesList
        self.message = message

        # Feedback channel: the gateway pushes this message's subscriber count
        # here whenever it changes, so the sender can skip producing data
        # nobody reads (see hasSubscribers).
        self._pipeRecv, self._pipeSend = Pipe(duplex=False)
        self._subscriberCount = 0
        self.queuesList["Config"].put(
            {
                "Subscribe/Unsubscribe": "senderFeedback",
                "Owner": self.message.Owner.value,
                "msgID": self.message.msgID.value,
                "To": {"pipe": self._pipeSend},
            }
        )

    def hasSubscribers(self):
        """
        True while at least one subscriber is registered for this message,
        as reported by the gateway. Typical use:

            if self.sender.hasSubscribers():
                self.sender.send(expensive_payload)
        """
        while self._pipeRecv.poll():
            self._subscriberCount = self._pipeRecv.recv()
        return self._subscriberCount > 0

    def send(self, value):
        """
        Puts a value into the queuesList

        Args:
            value (any type): The value to be put into the queue. This can be of any type
        """
        self.queuesList[self.message.Queue.value].put(
            {
                "Owner": self.message.Owner.value,
                "msgID": self.message.msgID.value,
                "msgType": self.message.msgType.value,
                "msgValue": value
            }
        )