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

from threading import Thread
from multiprocessing import Pipe
from server_data import ServerData
from server_listener import ServerListener
from server_subscriber import ServerSubscriber
from streamer import Streamer

import time
import random

class EnvironmentalHandler(Thread):
    
    def __init__(self, ID, beacon, serverpublickey, streamPipe, clientprivatekey):
        """ EnvironmentalHandler targets to connect on the server and to send messages, which incorporates 
        the coordinate of the encountered obstacles on the race track. It has two main state, the setup state and the streaming state. 
        In the setup state, it creates the connection with server. It's sending the messages to the server in the streaming
        state. 

        It's a thread, so can be run parallel with other threads. You can write the coordinates and the id of the encountered obstacle 
        and the script will send it.

        """
        super(EnvironmentalHandler, self).__init__()
        #: serverData object with server parameters
        self.__server_data = ServerData(beacon)
        #: discover the parameters of server
        self.__server_listener = ServerListener(self.__server_data)
        #: connect to the server
        self.__subscriber = ServerSubscriber(self.__server_data, ID, serverpublickey, clientprivatekey)
        #: receive and decode the messages from the server
        self.__streamer = Streamer(self.__server_data, streamPipe)
        
        self.__running = True

    def setup(self):
        """Actualize the server's data and create a new socket with it.
        """
        # Running while it has a valid connection with the server
        while(self.__server_data.socket == None and self.__running):
            # discover the parameters of server
            self.__server_listener.find()
            if self.__server_data.is_new_server and self.__running:
                # connect to the server 
                self.__subscriber.subscribe()
        
    def stream(self):
        """ Listening the coordination of robot
        """
        self.__streamer.stream()

    def run(self):
        while(self.__running):
            self.setup()
            self.stream()
    
    def stop(self):
        """Terminate the thread running.
        """
        self.__running = False
        self.__server_listener.stop()
        self.__streamer.stop()

if __name__ == '__main__':
    beacon = 23456

    id = 120
    serverpublickey = 'publickey_livetraffic_server_test.pem'
    clientprivatekey = 'privatekey_livetraffic_client_test.pem'

    #: For testing purposes, with the provided simulated livetraffic_system, the pair of keys above is used
    #       -   "publickey_livetraffic_server_test.pem"     --> Ensure by the client that the server is the actual server
    #       -   "privatekey_livetraffic_client_test.pem"    --> Ensure by the server that the client is the actual client

    #: At Bosch location during the competition 
    #       -   Use the "publickey_livetraffic_server.pem" instead of the "publickey_livetraffic_server_test.pem" 
    #       -   As for the "publickey_livetraffic_client.pem", you will have to generate a pair of keys, private and public, using the following terminal lines.  Before the competition, instruction of where to send your publickey_livetraffic_client.pem will be given.

    #: openssl genrsa -out privateckey_livetraffic_client.pem 2048 ----> Creates a private ssh key and stores it in the current dir with the given name
    #: openssl rsa -in privateckey_livetraffic_client.pem -pubout -out publickey_livetraffic_client.pem ----> Creates the corresponding public key out of the private one. 

    #:
    #: To test the functionality, 
    #       -   copy the generated public key under test/livetrafficSERVER/keys 
    #       -   rename the key using this format: "id_publickey.pem" ,where the id is the id of the key you are trying to connect with
    #       -   The given example connects with the id 120 and the same key is saved with "120_publickey.pem"
    
    gpsStR, gpsStS = Pipe(duplex = False)

    envhandler = EnvironmentalHandler(id, beacon, serverpublickey, gpsStR, clientprivatekey)
    envhandler.start()
    time.sleep(5)
    for x in range(1, 10):
        time.sleep(random.uniform(1,5))
        a = {"obstacle_id": int(random.uniform(0,25)), "x": random.uniform(0,15), "y": random.uniform(0,15)}
        gpsStS.send(a)
        
    envhandler.stop()
    envhandler.join()
