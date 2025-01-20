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

import json
import time
from src.utils.messages.allMessages import Location
from src.utils.messages.messageHandlerSender import messageHandlerSender
from twisted.internet import protocol

# The server itself. Creates a new Protocol for each new connection and has the info for all of them.
class tcpClient(protocol.ClientFactory):
    def __init__(self, connectionBrokenCllbck, locsysID, locsysFrequency, queue):
        self.connectiondata = None
        self.connection = None
        self.retry_delay = 1
        self.connectionBrokenCllbck = connectionBrokenCllbck
        self.locsysID = locsysID
        self.locsysFrequency = locsysFrequency
        self.queue = queue
        self.sendLocation = messageHandlerSender(self.queue, Location)

    def clientConnectionLost(self, connector, reason):
        print(
            "Connection lost with server ",
            self.connectiondata,
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

    def send_data_to_server(self, message):
        self.connection.send_data(message)


# One class is generated for each new connection
class SingleConnection(protocol.Protocol):
    def connectionMade(self):
        peer = self.transport.getPeer()
        self.factory.connectiondata = peer.host + ":" + str(peer.port)
        self.factory.connection = self
        self.subscribeToLocaitonData(self.factory.locsysID, self.factory.locsysFrequency)
        print("Connection with server established : ", self.factory.connectiondata)

    def dataReceived(self, data):
        dat = data.decode()
        tmp_data = dat.replace("}{","}}{{")
        if tmp_data != dat:
            tmp_dat = tmp_data.split("}{")
            dat = tmp_dat[-1]
        da = json.loads(dat)

        if da["type"] == "location":
            da["id"] = self.factory.locsysID
            self.sendLocation.send_message(da)
        else:
            print(
                "got message from trafficcommunication server: ",
                self.factory.connectiondata,
            )
    def send_data(self, message):
        msg = json.dumps(message)
        self.transport.write(msg.encode())
    
    def subscribeToLocaitonData(self, id, frequency):
        # Sends the id you wish to subscribe to and the frequency you want to receive data. Frequency must be between 0.1 and 5. 
        msg = {
            "reqORinfo": "info",
            "type": "locIDsub",
            "locID": id,
            "freq": frequency,
        }
        self.send_data(msg)
    
    def unSubscribeToLocaitonData(self, id, frequency):
        # Unsubscribes from locaiton data. 
        msg = {
            "reqORinfo": "info",
            "type": "locIDubsub",
        }
        self.send_data(msg)
