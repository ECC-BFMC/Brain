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
# Import necessary modules

from twisted.internet import reactor
from src.templates.threadwithstop import ThreadWithStop
from src.data.TrafficCommunication.threads.udpListener import udpListener
from src.data.TrafficCommunication.threads.tcpClient import tcpClient
from src.data.TrafficCommunication.useful.periodicTask import periodicTask


class threadTrafficCommunication(ThreadWithStop):
    """Thread which will handle processTrafficCommunication functionalities

    Args:
        shrd_mem (sharedMem): A space in memory for mwhere we will get and update data.
        queuesList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        deviceID (int): The id of the device.
        decrypt_key (String): A path to the decription key.
    """

    # ====================================== INIT ==========================================
    def __init__(self, shrd_mem, queueslist, deviceID, frequency, decrypt_key):
        super(threadTrafficCommunication, self).__init__()
        self.listenPort = 9000
        self.queue = queueslist

        self.tcp_factory = tcpClient(self.serverLost, deviceID, frequency, self.queue) # Handles the connection with the server

        self.udp_factory = udpListener(decrypt_key, self.serverFound) #Listens for server broadcast and validates it

        self.period_task = periodicTask(1, shrd_mem, self.tcp_factory) # Handles the Queue of errors accumulated so far.

        self.reactor = reactor
        self.reactor.listenUDP(self.listenPort, self.udp_factory)

    # =================================== CONNECTION =======================================
    def serverLost(self):
        """If the server disconnects, we stop the factory listening and start the reactor listening"""

        self.reactor.listenUDP(self.listenPort, self.udp_factory)
        self.tcp_factory.stopListening()
        self.period_task.stop()

    def serverFound(self, address, port):
        """If the server was found, we stop the factory listening, connect the reactor, and start the periodic task"""
        
        self.reactor.connectTCP(address, port, self.tcp_factory)
        self.udp_factory.stopListening()
        self.period_task.start()



    # ======================================= RUN ==========================================
    def run(self):
        self.reactor.run(installSignalHandlers=False)

    # ====================================== STOP ==========================================
    def stop(self):
        self.reactor.stop()
        super(threadTrafficCommunication, self).stop()
