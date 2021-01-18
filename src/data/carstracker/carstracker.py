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
import json

# Port used for broadcast
PORT = 50009

##  listener class. 
#
#  Class used for running port listener algorithm 
class listener(Thread):
    
    ## Constructor.
	#  @param self          The object pointer.
    def __init__(self):
        
        # Flag indincating thread state
        self.RUN_LISTENER = False
        
        # Communication parameters, create and bind socket
        self.PORT = PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #(internet, UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.PORT))

        # Debug msg
        print("Created listener ")

        # Values extracted from message
        self.ID = 0
        self.pos = complex(0,0)
        self.ang = complex(0,0)

        Thread.__init__(self) 

    ## Method for running listener algorithm.
    #  @param self        The object pointer.
    def run(self):
        # Listen for incomming commands
        while self.RUN_LISTENER:
            # wait for data
            try:
                data,_ = self.sock.recvfrom(4096) # buffer size is 1024 bytes
                # Decode received data
                data = data.decode("utf-8") 
                data = json.loads(data)
                # Process data and extract ID, position coordinates and orientation
                self.processData(data)
            except Exception as e:
                print("Receiving data failed with error: " + str(e))

    ## Method for starting listener process.
    #  @param self          The object pointer.
    def start(self):
        self.RUN_LISTENER = True

        super(listener,self).start()

    ## Method for stopping listener process.
    #  @param self          The object pointer.
    def stop(self):
        self.RUN_LISTENER = False

    ## Method for processing received data.
    #  @param self          The object pointer.
    #  @param data          The string received on PORT ("ID, position(complex no.), orientation(complex no.)").
    def processData(self,data):
        # Get ID
        self.ID = int(data['id'])
        # Get position
        self.pos = complex(data['coor'])
        # Get orientation
        self.ang = complex(data['rot'])
        # Debug message
        to_print = "ID: {}, poition: {}, orientation: {}.".format(self.ID,self.pos,self.ang)
        print(to_print)

## Method for running the listener thread (for testing purposes).
#  @param none
def runListener():
    # Get time stamp when starting tester
    start_time = time.time()
    # Create listener object
    Listener = listener()
    # Start the listener
    Listener.start()
    # Wait until 10 seconds passed
    while (time.time()-start_time < 10):
        time.sleep(0.5)
    # Stop the listener
    Listener.stop()

if __name__ == "__main__":
    runListener()