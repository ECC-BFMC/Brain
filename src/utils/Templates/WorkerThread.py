import threading
from threading import Thread

class WorkerThread(Thread):
    def __init__(self, inPs, outPs):
        Thread.__init__(self)

        self.inQs = inQs
        self.outQs = outQs

        self.threads = list()

    
    def _init_threads(self):
        raise NotImplementedError
        
    