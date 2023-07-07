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
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)).split("Brain")[0] + "Brain/")



import serial

from src.templates.workerprocess            import WorkerProcess
from src.hardware.serialhandler.filehandler import FileHandler
from src.hardware.serialhandler.readthread  import ReadThread
from src.hardware.serialhandler.writethread import WriteThread


class processSerialHandler(WorkerProcess):
    # ===================================== INIT =========================================
    def __init__(self,queueList, logging, debugging=False):
        super(processSerialHandler,self).__init__(self.queuesList)

        devFile = '/dev/ttyACM0'
        logFile = 'historyFile.txt'
        
        # comm init       
        self.serialCom = serial.Serial(devFile,19200,timeout=0.1)
        self.serialCom.flushInput()
        self.serialCom.flushOutput()

        # log file init
        self.historyFile = FileHandler(logFile)

        self.queuesList = queueList
        self.logger = logging
        self.debugging = debugging

    # ===================================== STOP ==========================================
    def _stop(self):
        for thread in self.threads:
            thread.stop()
            thread.join()
        super(processSerialHandler,self).stop()

    # ===================================== RUN ==========================================
    def run(self):
        super(processSerialHandler,self).run()
        #Post running process -> close the history file
        self.historyFile.close()

    # ===================================== INIT TH =================================
    def _init_threads(self):
        """ Initializes the read and the write thread.
        """
        # read write thread        
        readTh  = ReadThread(self.serialCom,self.historyFile,self.queuesList)
        self.threads.append(readTh)
        writeTh = WriteThread(self.queuesList[0], self.serialCom, self.historyFile)
        self.threads.append(writeTh)
    
# =================================== EXAMPLE ========================================= 
#             ++    THIS WILL RUN ONLY IF YOU RUN THE CODE FROM HERE  ++
#                  in terminal:    python3 processSerialHandler.py
if __name__ == "__main__":
    from multiprocessing import Queue, Event
    import logging

    allProcesses = list()

    debugg = False

    #We have a list of multiprocessing.Queue() which individualy represent a priority for processes.
    queueList = {"Critical": Queue(),
                 "Warning": Queue(), 
                 "General": Queue(), 
                 "Config": Queue()}

    logger  = logging.getLogger()
    process = processSerialHandler(queueList, logger, debugg)
    allProcesses.append(process)

    for process in allProcesses:
        process.daemon = True
        process.start()

# ===================================== STAYING ALIVE ====================================
    blocker = Event()  
    try:
        blocker.wait()
    except KeyboardInterrupt:
        print("\nCatching a KeyboardInterruption exception! Shutdown all processes.\n")
        for proc in allProcesses:
            if hasattr(proc,'stop') and callable(getattr(proc,'stop')):
                print("Process with stop",proc)
                proc.stop()
                proc.join()
            else:
                print("Process witouth stop",proc)
                proc.terminate()
                proc.join()
    

    





