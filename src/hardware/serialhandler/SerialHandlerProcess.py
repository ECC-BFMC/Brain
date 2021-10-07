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

import serial

from src.templates.workerprocess            import WorkerProcess
from src.hardware.serialhandler.filehandler import FileHandler
from src.hardware.serialhandler.ReadThread  import ReadThread
from src.hardware.serialhandler.WriteThread import WriteThread


class SerialHandlerProcess(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self,inPs, outPs):
        """The functionality of this process is to redirectionate the commands from the RemoteControlReceiverProcess (or other process) to the 
        micro-controller via the serial port. The default frequency is 256000 and device file /dev/ttyACM0. It automatically save the sent 
        commands into a log file, named historyFile.txt. 
        
        Parameters
        ----------
        inPs : list(Pipes)
            A list of pipes, where the first element is used for receiving the command to control the vehicle from other process.
        outPs : None
            Has no role.
        """
        super(SerialHandlerProcess,self).__init__(inPs, outPs)

        devFile = '/dev/ttyACM0'
        logFile = 'historyFile.txt'
        
        # comm init       
        self.serialCom = serial.Serial(devFile,256000,timeout=0.1)
        self.serialCom.flushInput()
        self.serialCom.flushOutput()

        # log file init
        self.historyFile = FileHandler(logFile)
        
    
    def run(self):
        super(SerialHandlerProcess,self).run()
        #Post running process -> close the history file
        self.historyFile.close()

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        """ Initializes the read and the write thread.
        """
        # read write thread        
        readTh  = ReadThread(self.serialCom,self.historyFile)
        self.threads.append(readTh)
        writeTh = WriteThread(self.inPs[0], self.serialCom, self.historyFile)
        self.threads.append(writeTh)
    

    

    





