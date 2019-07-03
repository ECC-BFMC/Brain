import sys
sys.path.append('.')

import json
import socket
import struct
import multiprocessing

from threading       import Thread
from multiprocessing import Process

from src.utils.Templates.WorkerProcess import WorkerProcess

class RemoteControlReceiver(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self, inPs, outPs):
        """Run on raspberry. Sends control messages received from socket to the serial 
        handler
        
         Arguments:
            inPs {list(Pipe)} -- []
            outPs {list(Pipe)} -- output pipes (order does not matter)
        """

        WorkerProcess.__init__(self, inPs, outPs)


        self.inPs       =   inPs
        self.outPs      =   outPs

        self.threads = list()

        self.port       =   12244
        self.serverIp   =   '0.0.0.0'
    # ===================================== RUN ==========================================
    def run(self):
        self._init_threads()
        self._init_socket()

        for th in self.threads:
            th.daemon = True
            th.start()
        
        for th in self.threads:
            th.join()

    # ===================================== INIT SOCKET ==================================
    def _init_socket(self):
        self.server_socket = socket.socket(
                                    family  = socket.AF_INET, 
                                    type    = socket.SOCK_DGRAM
                                )
        self.server_socket.bind((self.serverIp, self.port))

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        readTh = Thread(target = self._read_stream, args = (self.outPs, ))
        self.threads.append(readTh)

    # ===================================== READ STREAM ==================================
    def _read_stream(self, outPs):
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