import serial

from src.utils.Templates.WorkerProcess      import WorkerProcess
from src.hardware.SerialHandler.FileHandler import FileHandler

class SerialHandler(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self,inPs, outPs):
        """The functionality of this process is to redirectionate the commands from the remote or other process to the micro-controller by serial port.
        The default frequency is 460800 and device file /dev/ttyACM0. It automatically save the sent commands into a log file, named historyFile.txt. 
        
        Parameters
        ----------
        inPs : list(Pipes)
            A list of pipes, where the first element is used for receiving the command to control the vehicle from other process.
        outPs : None
            Has no role.
        """
        super(SerialHandler,self).__init__(inPs, outPs)

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
        """ Initializes the read and the write thread.
        """
        # read write thread        
        readTh  = ReadThread(1,self.serialCom,self.historyFile)
        self.threads.append(readTh)
        writeTh = WriteThread(self.inPs[0], self.serialCom, self.historyFile)
        self.readTh.append(writeTh)




