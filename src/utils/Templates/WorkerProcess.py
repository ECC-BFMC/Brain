import multiprocessing
from multiprocessing import Process

class WorkerProcess(Process):
    
    def __init__(self, inPs, outPs, daemon = True):
        Process.__init__(self)

        self.inPs = inPs
        self.outPs = outPs

        self.daemon = daemon
        self.threads = list()

    
    def _init_threads(self):
        raise NotImplementedError

    def run(self):
        self.init_threads()

        for th in self.threads:
            th.daemon = self.daemon
            th.start()

        for th in self.threads:
            th.join()