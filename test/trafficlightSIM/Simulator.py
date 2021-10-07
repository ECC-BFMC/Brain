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
from itertools import cycle
import json

class sim(Thread):


    def __init__(self):
        """Class used for running broadcaster algorithm for simulated semaphores.
        """
        
        #: Flag indincating thread state
        self.RUN_ADV = False
        
        # Communication parameters, create and bind socket
        self.PORT = 50007
        self.BCAST_ADDRESS = '<broadcast>'

        # Create a UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.server_address = (self.BCAST_ADDRESS, self.PORT)

        #: Patterns to be sent
        self.pattern_main = [0,0,0,0,0,1,1,2,2,2,2,2,1,1]
        self.pattern_start = [2,2,2,2,2,1,1,0,0,0,0,0,1,1]

        #: Cycles of patterns
        self.maincycle = cycle(self.pattern_main)
        self.startcycle = cycle(self.pattern_start)

        # Debug msg
        print("Created advertiser")

        Thread.__init__(self) 

    def run(self):
        """Method for running the simulation.
        """
        
        # Initializations
        old_time = time.time()
        main_state = next(self.maincycle)
        start_state = next(self.startcycle)

        # Send broadcast messages
        while self.RUN_ADV:
            
            #: Change pattern element each second
            if ((time.time()-old_time)>1):
                main_state = next(self.maincycle)
                start_state = next(self.startcycle)
                old_time = time.time()

            #: Send the data each 0.1 s
            try:
                # send the data for each semaphore
                self.sendState(1,main_state)
                self.sendState(2,main_state)
                self.sendState(3,start_state)
            except Exception as e:
                print("Sending data failed with error: " + str(e))

            # wait for 0.1 s before next broadcast msg
            time.sleep(0.1)

    def start(self):
        """Method for starting the process.
        """
        self.RUN_ADV = True

        super(sim,self).start()


    def stop(self):
        """Method for stopping the process.
        """
        self.RUN_ADV = False

    # 
    #  @param self          The object pointer.
    #  @param id            
    #  @param          
    def sendState(self,id,state):
        """Method that sends the ID and semaphore state.

        :param ID: The semaphore ID
        :type ID: int
        :param state: The semaphore state (0 - RED, 1 - Yellow, 2 - Green)
        :type state: int
        """

        # Send data
        value = {"id":id, "state":state}
        message = json.dumps(value)
        # Debug message
        # print('sending {!r}'.format(message))
        sent = self.sock.sendto(message.encode('utf-8'), self.server_address)

def runAdvertiser():
    """Method for sending the simulated semaphore signals.
    """
    # Get time stamp when starting tester
    start_time = time.time()
    # Create broadcaster object
    Adv = sim()
    # Start the broadcaster
    Adv.start()
    # Wait until 60 seconds passed
    while (time.time()-start_time < 60):
        time.sleep(0.5)
    # Stop the broadcaster
    Adv.stop()

if __name__ == "__main__":
    runAdvertiser()