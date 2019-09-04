import sys
sys.path.append('.')

import time
import socket
import struct
import numpy as np


import cv2
from threading import Thread

import multiprocessing
from multiprocessing import Process

from src.utils.Templates.WorkerProcess import WorkerProcess


class CameraReceiver(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self, inPs, outPs):
        """Process used for debugging. It receives the images from the raspberry and 
        duplicates the perception pipline that is running on the raspberry.

        Parameters
        ----------
        inPs : list(Pipe)  
            List of input pipes
        outPs : list(Pipe) 
            List of output pipes
        """
        super(CameraReceiver,self).__init__(inPs, outPs)

        self.port       =   2244
        self.serverIp   =   '0.0.0.0'

        self.imgSize    = (480,640,3)
    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializers and start the threads. 
        """
        self._init_socket()
        self._init_threads()

        for th in self.threads:
            th.daemon = True
            th.start()

        for th in self.threads:
            th.join()

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        """Initialize the socket. 
        """
        self.server_socket = socket.socket()
        self.server_socket.bind((self.serverIp, self.port))
        self.server_socket.listen(0)

        self.connection = self.server_socket.accept()[0].makefile('rb')

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        """Initialize the read thread to receive the video.
        """
        readTh = Thread(target = self._read_stream, args = (self.outPs, ))
        self.threads.append(readTh)

    # ===================================== READ STREAM ==================================
    def _read_stream(self, outPs):
        """Read the image from input stream, decode it and show it.
        
        Parameters
        ----------
        outPs : list(Pipe)
            output pipes (not used at the moment)
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

        finally:
            self.connection.close()
            self.server_socket.close()


if __name__ =='__main__':
    a = CameraReceiver([],[])
    a.start()
    a.join()