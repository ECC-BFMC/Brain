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
import src.data.TrafficCommunication.useful.keyDealer as keyDealer


class udpListener(protocol.DatagramProtocol):
    """This class will handle the connection.

    Args:
        decrypt_key (String): A path to the decripting key.
        serverfound (function): This function will be called if the server will be found.
    """

    def __init__(self, decrypt_key, serverfound):
        decrypt_key = decrypt_key
        self.pub_key = keyDealer.load_public_key(decrypt_key)
        self.serverfoundCllback = serverfound

    def startProtocol(self):
        print("Looking for Traffic Communicaiton Server")

    def datagramReceived(self, datagram, address):
        """In this function we split the receive data and we call the callbackfunction"""
        try:
            dat = datagram.split(b"(-.-)")
            if len(dat) != 2:
                raise Exception("Plaintext or signature not present")
            a = keyDealer.verify_data(self.pub_key, dat[1], dat[0])
            if not a:
                raise Exception("signature not valid")
            msg = dat[1].decode().split(":")
            port = int(msg[1])
            self.serverfoundCllback(address[0], port)
        except Exception as e:
            print(e)

    def stopListening(self):
        self.transport.stopListening()
