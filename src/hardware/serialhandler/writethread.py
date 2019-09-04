import threading 
from threading import Thread

class WriteThread():
    # ===================================== INIT =========================================
    def __init__(self, inP, serialCom, logFile):
        """The purpose of this thread is to redirectionate the received through input pipe to an other device by using serial communication. 
        
        Parameters
        ----------
        inP : multiprocessing.Pipe 
            Input pipe to receive the command from an other process.
        serialCom : serial.Serial
            The serial connection interface between the two device.
        logFile : FileHandler
            The log file handler to save the commands. 
        """
        self.inP        =  inPs
        self.serialCom  =  serialCom
        self.logFile    =  logFile

    # ===================================== RUN ==========================================
    def run(self):
        """ Represents the thread activity to redirectionate the message.
        """
        while True:
            command = self.inP.recv()

            self.serialCom.send(command.encode('ascii'))
            self.logFile.write(command.encode('ascii'))


