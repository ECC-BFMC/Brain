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
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWITrueSE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

from multiprocessing import connection

from src.templates.threadwithstop import ThreadWithStop
from src.utils.logConfig import get_logger

class threadGateway(ThreadWithStop):
    """Thread which will handle processGateway functionalities.\n
    Args:
        queuesList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        debugger (bool): A flag for debugging.
    """

    # ===================================== INIT =========================================

    def __init__(self, queueList, debugging):
        # pause=0: thread_work blocks on the queues themselves, no extra sleep needed
        super(threadGateway, self).__init__(pause=0)
        self.logger = get_logger("Gateway")
        self.debugging = debugging
        self.sendingList = {}
        self.queuesList = queueList
        self.messageApproved = []
        self.senderFeedback = {}
        self._queueReaders = [
            self.queuesList[name]._reader
            for name in ("Critical", "Warning", "General", "Config")
            if name in self.queuesList
        ]

    # =================================== SUBSCRIBE ======================================

    def subscribe(self, message):
        """This functin will add the pipe into the approved messages list and it will be added into the dictionary of sending
        Args:
            message(dictionary): Dictionary received from the multiprocessing queues ( the config one).
        """
        
        # Declaration of variables:
        Owner = message["Owner"]
        Id = message["msgID"]
        To = message["To"]["receiver"]
        Pipe = message["To"]["pipe"]
        if not Owner in self.sendingList.keys():
            self.sendingList[Owner] = {}
        if not Id in self.sendingList[Owner].keys():
            self.sendingList[Owner][Id] = {}
        if not To in self.sendingList[Owner][Id].keys():
            self.sendingList[Owner][Id][To] = Pipe
        self.messageApproved.append((Owner, Id))

        self._notifySenders(Owner, Id)

        # Debugging( you can comment this):
        if self.debugging:
            self.print_list()

    # ================================== UNSUBSCRIBE =====================================

    def unsubscribe(self, message):
        """This functin will remove the pipe into the approved messages list and it will be added into the dictionary of sending
        Args:
            message(dictionary): Dictionary received from the multiprocessing queues ( the config one).
        """

        Owner = message["Owner"]
        Id = message["msgID"]
        To = message["To"]["receiver"]

        # Guarded delete: an unsubscribe for something never subscribed must not
        # raise here, it would kill message routing for the whole application.
        pipes = self.sendingList.get(Owner, {}).get(Id, {})
        if To in pipes:
            del pipes[To]
        else:
            self.logger.warning(f"Unsubscribe for unknown subscription: {Owner}/{Id}/{To}")
        if (Owner, Id) in self.messageApproved:
            self.messageApproved.remove((Owner, Id))

        self._notifySenders(Owner, Id)

        if self.debugging:
            self.print_list()

    # ============================= SENDER FEEDBACK ======================================

    def registerSender(self, message):
        """Registers a sender's feedback pipe for its message. The gateway
        immediately reports the current subscriber count (so senders created
        after subscribers start correct) and pushes every later change; the
        sender exposes it as hasSubscribers()."""
        Owner = message["Owner"]
        Id = message["msgID"]
        pipe = message["To"]["pipe"]
        self.senderFeedback.setdefault((Owner, Id), []).append(pipe)
        self._notifySenders(Owner, Id)

    def _notifySenders(self, owner, msgId):
        """Pushes the current subscriber count of (owner, msgId) to all of its
        registered senders."""
        pipes = self.senderFeedback.get((owner, msgId))
        if not pipes:
            return
        count = len(self.sendingList.get(owner, {}).get(msgId, {}))
        for pipe in list(pipes):
            try:
                pipe.send(count)
            except Exception:
                pipes.remove(pipe)  # the sender's process is gone

    # =================================== SENDING ========================================

    def send(self, message):
        """This functin will send the message on all the pipes that are in the sending list of the message ID.
        Args:
            message(dictionary): Dictionary received from the multiprocessing queues ( the config one).
        """

        Owner = message["Owner"]
        Id = message["msgID"]
        Type = message["msgType"]
        Value = message["msgValue"]
        if (Owner, Id) in self.messageApproved:
            for element in self.sendingList[Owner][Id]:
                # We send a dictionary that contain the type of the message and message
                self.sendingList[Owner][Id][element].send(
                    {"Type": Type, "value": Value, "id": Id, "Owner": Owner}
                )
                if self.debugging:
                    self.logger.warning(message)

    # ====================================================================================

    # Function for debugging:
    def print_list(self):
        """Made for debugging"""

        self.logger.warning(self.sendingList)

    # ==================================== RUN ===========================================

    def thread_work(self):
        """This function will take the messages in priority order form the queues.\n
        the prioirty is: Critical > Warning > General

        It blocks until any queue has data (instead of polling every millisecond),
        then drains everything that is available before blocking again.
        """

        if not self._queueReaders:
            self._blocker.wait(0.1)
            return

        # Sleep until at least one queue has data. The timeout only bounds how
        # fast we notice a stop() request, not the message latency.
        if not connection.wait(self._queueReaders, timeout=0.1):
            return

        # Handle subscriptions first so they apply before the data fan-out.
        while not self.queuesList["Config"].empty():
            message2 = self.queuesList["Config"].get()
            action = str.lower(message2["Subscribe/Unsubscribe"])
            if action == "subscribe":
                self.subscribe(message2)
            elif action == "senderfeedback":
                self.registerSender(message2)
            else:
                self.unsubscribe(message2)

        # Drain the data queues in priority order (Critical > Warning > General),
        # re-checking the higher priority queues after every message.
        while not self._blocker.is_set():
            if not self.queuesList["Critical"].empty():
                message = self.queuesList["Critical"].get()
            elif not self.queuesList["Warning"].empty():
                message = self.queuesList["Warning"].get()
            elif not self.queuesList["General"].empty():
                message = self.queuesList["General"].get()
            else:
                break
            self.send(message)
