import multiprocessing
from multiprocessing import Process

class WorkerProcess(Process):

    def __init__(self, inPs, outPs, daemon = True):
        """WorkerProcess is an abstract class for description a general structure and interface a process.
        
        Parameters
        ----------
        inPs : list(Pipe)
            input pipes 
        outPs : list(Pipe)
            output pipes 
        daemon : bool, optional
            daemon process flag, by default True
        """
        super(WorkerProcess,self).__init__()

        self.inPs = inPs
        self.outPs = outPs

        self.daemon = daemon
        self.threads = list()

    
    def init_threads(self):
        """ Initialize the threads of the process.

        Raises
        ------
        NotImplementedError
            Have to implement the initialization of threads
        """
        raise NotImplementedError

    def run(self):
        """This method applies the initialization of the theards and starts all of them. The process will shutdown, when all of the threads have stoped.
        """
        self.init_threads()

        for th in self.threads:
            th.daemon = self.daemon
            th.start()

        for th in self.threads:
            th.join()