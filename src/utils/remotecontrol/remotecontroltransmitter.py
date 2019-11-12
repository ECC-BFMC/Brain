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

from threading       import  Thread
from multiprocessing import  Pipe

from src.utils.remotecontrol.rcbrain            import RcBrain
from src.utils.remotecontrol.keyboardlistener   import KeyboardListener
from src.utils.templates.workerprocess          import WorkerProcess

class RemoteControlTransmitter(Thread):
    # ===================================== INIT==========================================
    def __init__(self,  inPs = [], outPs = []):
        """Remote controller transmitter. This should run on your PC. 
        
        """
        super(RemoteControlTransmitter,self).__init__()

        # Can be change to a multithread.Queue.
        self.lisBrR, self.lisBrS = Pipe(duplex=False)

        self.rcBrain   =  RcBrain()
        self.listener  =  KeyboardListener([self.lisBrS])

        self.port      =  12244
        self.serverIp  = '192.168.1.2'

        self.threads = list()
    # ===================================== RUN ==========================================
    def run(self):
        """Apply initializing methods and start the threads. 
        """
        self._init_threads()
        self._init_socket()
        for th in self.threads:
            th.start()

        for th in self.threads:
            th.join()

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        """Initialize the command sender thread for transmite the receiver process all commands. 
        """
        self.listener.daemon = self.daemon
        self.threads.append(self.listener)
        
        sendTh = Thread(name = 'SendCommand',target = self._send_command_thread, args=(self.lisBrR, ),daemon=self.daemon)
        self.threads.append(sendTh)

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        """Initialize the socket for communication with remote client.
        """
        self.client_socket = socket.socket(
                                family  = socket.AF_INET, 
                                type    = socket.SOCK_DGRAM
                            )

    # ===================================== SEND COMMAND =================================
    def _send_command_thread(self, inP):
        """Transmite the command to the remotecontrol receiver. 
        
        Parameters
        ----------
        inP : Pipe
            Input pipe. 
        """
        while True:
            key = inP.recv()

            command = self.rcBrain.getMessage(key)
            command = json.dumps(command).encode()

            size = len(command)

            self.client_socket.sendto(command,(self.serverIp,self.port))