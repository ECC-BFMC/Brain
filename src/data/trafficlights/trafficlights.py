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
# Module used for communication
import socket
import json


class trafficlights(Thread):
    def __init__(self):
        """listener class. 
        
        Class used for running port listener algorithm 
        """
        #: Flag indincating thread state
        self.RUN_LISTENER = False

        # Semaphore states
        self.s1_state=0 
        self.s2_state=0 
        self.s3_state=0 
        self.s4_state=0 

        #: Semaphore colors
        self.colors = ['red','yellow','green']

        # Debug msg
        print("Created listener ")

        Thread.__init__(self) 

    def start(self):
        """Method for starting listener process.
        """
        self.RUN_LISTENER = True
        # Debug msg
        self._init_socket()
        print("Started listener ")

        super(trafficlights,self).start()

    def _init_socket(self):
        # Communication parameters, create and bind socket
        self.PORT = 50007
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #(internet, UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.bind(('', self.PORT))
        self.sock.settimeout(1)

    def run(self):
        while self.RUN_LISTENER:
            # Wait for data
            try:
                data, addr = self.sock.recvfrom(4096) # buffer size is 1024 bytes
                dat = data.decode('utf-8')
                dat = json.loads(dat)
                ID = int(dat['id'])
                state = int(dat['state'])
                if (ID == 1):
                    self.s1_state=state
                elif (ID == 2):
                    self.s2_state=state
                elif (ID == 3):
                    self.s3_state=state
                elif (ID == 4):
                    self.s4_state=state

            except Exception as e:
                print("Receiving data failed with error: " + str(e))

    
    def stop(self):
        """ Method for stopping listener process.
        """
        self.RUN_LISTENER = False

    def get_S1(self):
        """Method for getting S1 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s1_state


    def get_S2(self):
        """Method for getting S2 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s2_state


    def get_S3(self):
        """Method for getting S3 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s3_state
    
    def get_S4(self):
        """Method for getting S3 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s3_state
