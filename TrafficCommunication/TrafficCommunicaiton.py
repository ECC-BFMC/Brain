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

import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)).split("data")[0])

from twisted.internet           import reactor
from templates.threadwithstop   import ThreadWithStop
from multiprocessing            import Pipe

from udpListener                import udpListener
from tcpClient                  import tcpClient
from tcpLocsys                  import tcpLocsys
from useful.periodicTask        import periodicTask
from useful.sharedMem           import sharedMem

class TrafficCommunication(ThreadWithStop):
    def __init__(self, shrd_mem, locsysSendPipe, deviceID, decrypt_key, listenPort=9000):
        super(TrafficCommunication,self).__init__()
        
        self.listenPort = listenPort

        self.tcp_factory = tcpClient(self.serverDisconnect, self.locsysConnect, deviceID)
        self.udp_factory = udpListener(decrypt_key, self.serverFound)
        self.tcp_factory_locsys = tcpLocsys(locsysSendPipe)

        self.period_task = periodicTask(1, shrd_mem, self.tcp_factory)

        self.reactor = reactor
  
        self.reactor.listenUDP(self.listenPort, self.udp_factory)
    
    def serverDisconnect(self):
        self.reactor.listenUDP(self.listenPort, self.udp_factory)
        self.tcp_factory.stopListening()

    def serverFound(self, address, port):
        self.reactor.connectTCP(address, port, self.tcp_factory)
        self.udp_factory.stopListening()

    def locsysConnect(self, IPandPORT):
        ip, port = IPandPORT.split(":")
        self.reactor.connectTCP(ip, int(port), self.tcp_factory_locsys)
    
    def run(self):
        self.period_task.start()
        self.reactor.run(installSignalHandlers=False)

    def stop(self):
        self.reactor.stop()
        super(TrafficCommunication,self).stop()
        

if __name__ == "__main__":
    shared_memory = sharedMem()
    locsysReceivePipe, locsysSendPipe   = Pipe(duplex = False)
    
    # filename = "test/TrafficCommunicationServer/publickey_server.pem"
    filename = "test/TrafficCommunicationServer/publickey_server_test.pem"
    deviceID = 3

    traffic_communication = TrafficCommunication(shared_memory, locsysSendPipe, deviceID, filename)
    traffic_communication.start() 

    import random
    import time
    # for devicepos [x,y] is expected
    # for deviceRot [theta] is expected
    # for deviceSpeed [m/s] is expected
    # for historyData [id,x,y] is expected.
    msg = ["devicePos", "deviceRot", "deviceSpeed","historyData"] 

    try:
        while True:
            values = random.randint(1,3)
            val = []
            if values > 0: val.append(2.3)
            if values > 1: val.append(3.3)
            if values > 2: val.append(4.3)

            m = random.choice(msg)

            shared_memory.insert(m, val)

            print(shared_memory)

            if locsysReceivePipe.poll():
                print(locsysReceivePipe.recv())

            time.sleep(0.5)


    
    except KeyboardInterrupt:
        traffic_communication.stop()
        traffic_communication.join()