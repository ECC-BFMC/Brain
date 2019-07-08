import threading
from threading import Lock

class FileHandler:

    def __init__(self,f_fileName):
        self.outFile = open(f_fileName,'w')
        self.lock    = Lock()

    def write(self,f_str):
        self.lock.acquire()
        self.outFile.write(f_str)
        self.lock.release()        
    
    def close(self):
        self.outFile.close()