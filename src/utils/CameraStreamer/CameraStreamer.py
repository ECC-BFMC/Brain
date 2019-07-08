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
        image is compresssed before it is send. 

        Used for visualizing your raspicam from PC.
        
        Arguments:
            inPs {list(Pipe)} -- []]
            outPs {list(Pipe)} -- output pipes (order does not matter)
        """
        WorkerProcess.__init__(self, inPs, outPs)

        self.serverIp   =  '192.168.1.141' # PC ip
        self.port       =  2244           # com port
        
    # ===================================== RUN ==========================================
    def run(self):
        self._init_socket()
        self._init_threads()

        for th in self.threads:
            th.daemon = True
            th.start()
        
        for th in self.threads:
            th.join()
            
    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        streamTh = Thread(target = self._send_thread, args= (self.inPs[0], ))
        streamTh.daemon = True
        self.threads.append(streamTh)

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        self.client_socket = socket.socket()
        self.client_socket.connect((self.serverIp, self.port))

        self.connection = self.client_socket.makefile('wb') 
        
    # ===================================== SEND THREAD ==================================
    def _send_thread(self, inP):
        
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
            
