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
from twisted.internet import protocol
from src.utils.messages.allMessages import Location
import time
import json


# The server itself. Creates a new Protocol for each new connection and has the info for all of them.
class tcpLocsys(protocol.ClientFactory):
    """This handle the data received(position)

    Args:
        sendQueue (multiprocessing.Queue): We place the information on this queue.
    """

    def __init__(self, id, sendQueue):
        self.connection = None
        self.retry_delay = 1
        self.sendQueue = sendQueue
        self.deviceID = id

    def clientConnectionLost(self, connector, reason):
        print(
            "Connection lost with server ",
            self.connectiondata,
            " Retrying in ",
            self.retry_delay,
            " seconds... (Check password match, IP or server availability)",
        )
        self.connectiondata = None
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print(
            "Connection failed. Retrying in",
            self.retry_delay,
            "seconds... Possible server down or incorrect IP:port match",
        )
        print(reason)
        time.sleep(self.retry_delay)
        connector.connect()

    def buildProtocol(self, addr):
        conn = SingleConnection()
        conn.factory = self
        return conn

    def stopListening(self):
        super().stopListening()

    def receive_data_from_server(self, message):
        message["id"] = 3
        message_to_send = {
            "Owner": Location.Owner.value,
            "msgID": Location.msgID.value,
            "msgType": Location.msgType.value,
            "msgValue": message,
        }
        self.sendQueue.put(message_to_send)


# One class is generated for each new connection
class SingleConnection(protocol.Protocol):
    def connectionMade(self):
        peer = self.transport.getPeer()
        self.factory.connectiondata = peer.host + ":" + str(peer.port)
        self.factory.connection = self
        print("Connection with locsys established : ", self.factory.connectiondata)

    def dataReceived(self, data):
        dat = data.decode()
        da = json.loads(dat)
        self.factory.receive_data_from_server(da)
