import io
import socket
import struct
import time
import numpy as np
from multiprocessing import Process
from threading import Thread

import cv2

from src.utils.Templates.WorkerProcess import WorkerProcess

class CameraStreamer(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self, inPs, outPs):
        """Process used for sending images over the network. UDP protocol is used. The
        image is compressed before it is send. 

        Used for visualizing your raspicam from PC.
        
        Parameters
        ----------
        inPs : list(Pipe) 
            List of input pipes, only the first pipe is used to transfer the captured frames. 
        outPs : list(Pipe) 
            List of output pipes (not used at the moment)
        """
        super(CameraStreamer,self).__init__( inPs, outPs)

        self.serverIp   =  '192.168.1.141' # PC ip
        self.port       =  2244           # com port
        
    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializing methods and start the threads.
        """
        self._init_socket()
        self._init_threads()

        for th in self.threads:
            th.daemon = True
            th.start()
        
        for th in self.threads:
            th.join()
            
    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        """Initialize the sending thread.
        """
        streamTh = Thread(target = self._send_thread, args= (self.inPs[0], ))
        streamTh.daemon = True
        self.threads.append(streamTh)

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        """Initialize the socket. 
        """
        self.client_socket = socket.socket()
        self.client_socket.connect((self.serverIp, self.port))

        self.connection = self.client_socket.makefile('wb') 
        
    # ===================================== SEND THREAD ==================================
    def _send_thread(self, inP):
        """Sending the frames received thought the input pipe to remote client by using a socket. 
        
        Parameters
        ----------
        inP : Pipe
            Input pipe to read the frames from other process. 
        """
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        print('Start streaming')

        while True:
            try:
                stamps, image = inP.recv()
                 
                result, image = cv2.imencode('.jpg', image, encode_param)
                data   =  image.tobytes()
                size   =  len(data)

                self.connection.write(struct.pack("<L",size))
                self.connection.write(data)

            except Exception as e:
                print(e)
            
