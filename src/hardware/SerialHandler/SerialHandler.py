import serial

from src.utils.Templates.WorkerProcess      import WorkerProcess
from src.hardware.SerialHandler.FileHandler import FileHandler

class SerialHandler(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self,inPs, outPs):
        WorkerProcess.__init__(self, inPs, outPs)

        devFile = '/dev/ttyACM0'
        logFile = 'historyFile.txt'
        
        # comm init       
        self.serialCom = serial.Serial(f_device_File,460800,timeout=0.1)
        self.serialCom.flushInput()
        self.serialCom.flushOutput()

        # log file init
        self.historyFile = FileHandler(f_history_file)

    # ===================================== INIT THREADS =================================
    def init_threads(self):
        # read write thread        
        readTh  = ReadThread(1,self.serialCom,self.historyFile,460800)
        self.threads.append(readTh)
        writeTh = WriteThread(self.inPs[0], self.serialCom, self.historyFile)
        self.readTh.append(writeTh)




