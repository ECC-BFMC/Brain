import threading 
from threading import Thread

class WriteThread():
    # ===================================== INIT =========================================
    def __init__(self, inP, serialCom, logFile):
        self.inP        =  inPs
        self.serialCom  =  serialCom
        self.logFile    =  logFile

    # ===================================== RUN ==========================================
    def run(self):
        while True:
            command = self.inP.recv()

            self.serialCom.send(command.encode('ascii'))
            self.logFile.write(command.encode('ascii'))


