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
import json
import socket

from threading       import Thread

from src.utils.templates.workerprocess import WorkerProcess

class RemoteControlReceiver(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self, inPs, outPs):
        """Run on raspberry. It sends control messages received from socket to the serial 
        handler
        
        Parameters
        ------------
        inPs : list(Pipe)
            List of input pipes (not used at the moment)
        outPs : list(Pipe) 
            List of output pipes (order does not matter)
        """

        super(RemoteControlReceiver,self).__init__( inPs, outPs)

        self.port       =   12244
        self.serverIp   =   '0.0.0.0'
    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializing methods and start the threads
        """
        self._init_socket()
        super(RemoteControlReceiver,self).run()

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        """Initialize the communication socket
        """
        self.server_socket = socket.socket(
                                    family  = socket.AF_INET, 
                                    type    = socket.SOCK_DGRAM
                                )
        self.server_socket.bind((self.serverIp, self.port))

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        """Initialize the read thread to transmite the received messages to other processes. 
        """
        readTh = Thread(name='ReceiverCommand',target = self._read_stream, args = (self.outPs, ))
        self.threads.append(readTh)

    # ===================================== READ STREAM ==================================
    def _read_stream(self, outPs):
        """Receive the message and send forward to others. 
        
        Parameters
        ----------
        outPs : list(Pipe)
            List of the output pipes.
        """
        try:
            while True:
                
                bts, addr = self.server_socket.recvfrom(1024)

                bts     =  bts.decode()
                command =  json.loads(bts)

                for outP in outPs:
                    outP.send(command)

        except Exception as e:
            print(e)

        finally:
            self.server_socket.close()