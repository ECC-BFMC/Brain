import threading 
from threading import Thread
from src.hardware.serialhandler.messageconverter import MessageConverter
from src.utils.templates.threadwithstop import ThreadWithStop

class WriteThread(Thread):
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
        super(WriteThread,self).__init__()
        self.inP        =  inP
        self.serialCom  =  serialCom
        self.logFile    =  logFile
        self.messageConverter = MessageConverter()

    # ===================================== RUN ==========================================
    def run(self):
        """ Represents the thread activity to redirectionate the message.
        """
        while True:
            command = self.inP.recv()
            command_msg = self.messageConverter.get_command(**command)
            self.serialCom.write(command_msg.encode('ascii'))
            self.logFile.write(command_msg)


