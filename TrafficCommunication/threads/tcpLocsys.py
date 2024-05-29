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

    # def __init__(self, id, sendQueue):
    #     self.connection = None
    #     self.retry_delay = 1
    #     self.sendQueue = sendQueue
    #     self.deviceID = id

    def __init__(self, deviceID, sendQueue):
        self.connectiondata = None
        self.connection = None
        self.retry_delay = 1
        self.sendQueue = sendQueue
        self.deviceID = deviceID

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
        print('here3')
        conn.factory = self
        return conn

    #ClientFactory nu are metoda de stopListening??
    def stopListening(self):
        super().stopListening()

    # Ii confusing, nu ii from server ii from Location device (I guess)
    def receive_data_from_server(self, message):
        # De ce 3?
        message["id"] = self.deviceID
        
        print('here2')

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
<<<<<<< HEAD
        dat = data.decode()
        tmp_data = dat.replace("}{","}}{{")
        if tmp_data != dat:
            tmp_dat = tmp_data.split("}{")
            dat = tmp_dat[-1]
        da = json.loads(dat)
        self.factory.receive_data_from_server(da)
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
        try:
            dat = data.decode()
            da = json.loads(dat)
            self.factory.receive_data_from_server(da)
        except Exception as e:
            print(data)
            print("ttcpLocsys -> dataReceived (line 111)")
            print(e)

>>>>>>> 7f0d8187eee98a81dd404308b4f7846168b19f09
>>>>>>> e52a7757083565575dca9ee39896d3895fd38e29
>>>>>>> fe38f2896e92ca1a7a143585e198e8ce5f2b8b18
>>>>>>> 484bad0f91d4d3232a8d2db53e6a790eaa9c4390
>>>>>>> 9f158333fbaa1f1a3abf903cd8b87f40c81ac184
>>>>>>> 6519bd656912fa5fc5037b5c6894e84434d19d19
>>>>>>> ee658f9826666bf894b22c061e0d7a2460a2119e
