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
import json
import time


# The server itself. Creates a new Protocol for each new connection and has the info for all of them.
class tcpClient(protocol.ClientFactory):
    def __init__(self, connectionBrokenCllbck, locsysConnectCllbck, locsysID):
        self.connectiondata = None
        self.connection = None
        self.retry_delay = 1
        self.connectionBrokenCllbck = connectionBrokenCllbck
        self.locsysConnectCllbck = locsysConnectCllbck
        self.locsysID = locsysID

    def clientConnectionLost(self, connector, reason):
        print(
            "Connection lost with server ",
            self.connectiondata,
            " Retrying in ",
            self.retry_delay,
            " seconds... (Check Keypair, IP or server availability)",
        )
        try:
            self.connectiondata = None
            self.connection = None
            self.connectionBrokenCllbck()
        except:
            pass

    def clientConnectionFailed(self, connector, reason):
        print(
            "Connection failed. Retrying in",
            self.retry_delay,
            "seconds... Possible server down or incorrect IP:port match",
        )
        time.sleep(self.retry_delay)
        connector.connect()

    def buildProtocol(self, addr):
        conn = SingleConnection()
        conn.factory = self
        return conn

    def isConnected(self):
        if self.connection == None:
            return False
        else:
            return True

    def send_data_to_server(self, message):
        self.connection.send_data(message)

    def receive_data_from_server(self, message):
        msgPrepToList = message.replace("}{", "}}{{")
        msglist = msgPrepToList.split("}{")
        for msg in msglist:
            msg = json.loads(msg)
            if msg["reqORinfo"] == "request":
                if msg["type"] == "locsysDevice":
                    if "error" in msg:
                        print(msg["error"], "on traffic communication")
                    else:
                        self.locsysConnectCllbck(msg["DeviceID"], msg["response"])


# One class is generated for each new connection
class SingleConnection(protocol.Protocol):
    def connectionMade(self):
        peer = self.transport.getPeer()
        self.factory.connectiondata = peer.host + ":" + str(peer.port)
        self.factory.connection = self
        msg = {
            "reqORinfo": "request",
            "type": "locsysDevice",
            "DeviceID": self.factory.locsysID,
        }
        self.send_data(msg)
        print("Connection with server established : ", self.factory.connectiondata)

    def dataReceived(self, data):
        self.factory.receive_data_from_server(data.decode())
        print(
            "got message from trafficcommunication server: ",
            self.factory.connectiondata,
        )

    def send_data(self, message):
        msg = json.dumps(message)
        self.transport.write(msg.encode())
