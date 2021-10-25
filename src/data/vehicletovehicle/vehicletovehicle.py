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
import time
from threading import Thread
# Module used for communication
import socket
import json

##  listener class. 
#
#  Class used for running port listener algorithm 
class vehicletovehicle(Thread):
    
    def __init__(self):
        """listener class. 
        
        Class used for running port listener algorithm 
        """
        super(vehicletovehicle,self).start()

        # Values extracted from message
        self.ID = 0
        self.timestamp = 0.0
        self.pos = complex(0,0)
        self.ang = complex(0,0)

        self._init_socket()

        # Flag indincating thread state
        self.__running = True

    def _init_socket(self):
        # Communication parameters, create and bind socket
        self.PORT = 50007
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #(internet, UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.bind(('', self.PORT))
        self.sock.settimeout(1)


    def run(self):
        while self.__running:
            try:
                data,_ = self.sock.recvfrom(4096)
                data = data.decode("utf-8") 
                data = json.loads(data)

                self.ID = int(data['id'])

                self.timestamp = complex(data['timestamp'])

                self.pos = complex(data['coor'])

                self.ang = complex(data['rot'])
            except Exception as e:
                print("Receiving data failed with error: " + str(e))

    ## Method for stopping listener process.
    #  @param self          The object pointer.
    def stop(self):
        self.__running = False
