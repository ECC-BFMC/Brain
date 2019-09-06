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