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
sys.path.append('.')

import time
import socket
import struct
import numpy as np


import cv2
from threading import Thread

import multiprocessing
from multiprocessing import Process,Event

from src.templates.workerprocess import WorkerProcess


class CameraReceiverProcess(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self, inPs, outPs):
        """Process used for debugging. Can be used as a direct frame analyzer, instead of using the VNC
        It receives the images from the raspberry and displays them.

        Parameters
        ----------
        inPs : list(Pipe)  
            List of input pipes
        outPs : list(Pipe) 
            List of output pipes
        """
        super(CameraReceiverProcess,self).__init__(inPs, outPs)

        

        self.imgSize    = (480,640,3)
    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializers and start the threads. 
        """
        self._init_socket()
        super(CameraReceiverProcess,self).run()

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        """Initialize the socket server. 
        """
        self.port       =   2244
        self.serverIp   =   '0.0.0.0'
        
        self.server_socket = socket.socket()
        self.server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server_socket.bind((self.serverIp, self.port))

        self.server_socket.listen(0)
        self.connection = self.server_socket.accept()[0].makefile('rb')

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        """Initialize the read thread to receive and display the frames.
        """
        readTh = Thread(name = 'StreamReceivingThread',target = self._read_stream)
        self.threads.append(readTh)

    # ===================================== READ STREAM ==================================
    def _read_stream(self):
        """Read the image from input stream, decode it and display it with the CV2 library.
        """
        try:
            while True:

                # decode image
                image_len = struct.unpack('<L', self.connection.read(struct.calcsize('<L')))[0]
                bts = self.connection.read(image_len)

                # ----------------------- read image -----------------------
                image = np.frombuffer(bts, np.uint8)
                image = cv2.imdecode(image, cv2.IMREAD_COLOR)
                image = np.reshape(image, self.imgSize)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # ----------------------- show images -------------------
                cv2.imshow('Image', image) 
                cv2.waitKey(1)
        except:
            pass
        finally:
            self.connection.close()
            self.server_socket.close()
