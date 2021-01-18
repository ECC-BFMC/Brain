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

# Module imports
import time,sys
import math
from threading import Thread
# Module used for communication
import socket
import os
import sys

import position_listener_sim
import json

# ID of the mobile obstacle
ID = 100
# Port used for broadcast
PORT = 50009

##  Broadcaster class. 
#
#  Class used for running port broadcaster algorithm 
class Broadcaster(Thread):
    
    ## Constructor.
	#  @param self          The object pointer.
    def __init__(self,position_listener):
        
        # Flag indincating thread state
        self.RUN_BROADCASTER = False
        
        # Communication parameters, create and bind socket
        self.PORT = PORT
        self.BCAST_ADDRESS = '<broadcast>'

        # Create a UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.server_address = (self.BCAST_ADDRESS, self.PORT)

        #: Receive and decode the messages from the server
        self.__position_listener = position_listener

        self.__ID = ID

        # debug msg
        print("Created broadcaster")

        Thread.__init__(self) 

    ## Method for running broadcaster algorithm.
    #  @param self        The object pointer.
    def run(self):
        # Broadcast acuired position
        while self.RUN_BROADCASTER:
            # Send the data each 1 s
            try:
                # Send the data
                self.sendData()
            except Exception as e:
                print("Sending data failed with error: " + str(e))
            
            # Wait for 1 s before next adv
            time.sleep(1)

    ## Method for starting broadcaster process.
    #  @param self          The object pointer.
    def start(self):
        self.RUN_BROADCASTER = True

        super(Broadcaster,self).start()

    ## Method for stopping broadcaster process.
    #  @param self          The object pointer.
    def stop(self):
        self.RUN_BROADCASTER = False

    # Function that sends the local ID and car coordinates.
    #  @param self          The object pointer.
    def sendData(self):
        # Send data
        # The car ID
        id = self.__ID
        # Get new coordinates from listener
        coor = self.__position_listener.coor
        # Construct message to be sent
        value = {'id':id, 'coor':str(coor[0]), 'rot':str(coor[1])}
        message = json.dumps(value)
        # Debug msg
        print('sending {!r}'.format(message))
        self.sock.sendto(message.encode('utf-8'), self.server_address)

## Method for running the broadcaster (for testing purposes).
##            It uses the position_listener_sim module
#  @param none
def runBroadcaster():
    # Create the simulated listener
    my_position_listener = position_listener_sim.PositionListener()
    # Start the siumlated position listener
    my_position_listener.start()
    # Create broadcaster object
    broadcaster = Broadcaster(my_position_listener)
    # Start the broadcaster
    broadcaster.start()
    # Get time stamp when starting tester
    start_time = time.time()
    # Wait until 60 seconds passed
    while (time.time()-start_time < 60):
        time.sleep(0.5)
    # Stop the broadcaster
    broadcaster.stop()
    # Stop the siumlated position listener
    my_position_listener.stop()

if __name__ == "__main__":
    runBroadcaster()