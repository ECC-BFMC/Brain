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

    
    def _init_threads(self):
        """ It initializes the threads of the process and adds the thread to the 'threads' list, which will be automatically started and stopped in the 'run' method.

        Raises
        ------
        NotImplementedError
            Have to implement the initialization of threads
        """
        raise NotImplementedError

    def run(self):
        """This method applies the initialization of the theards and starts all of them. The process ignores the keyboardInterruption signal and can terminate by applying the 'stop' method. 
        The process will be blocked, until an other process use the 'stop' function. After appling the function it terminates all subthread.
        """
        self.init_threads()

        for th in self.threads:
            th.daemon = self.daemon
            th.start()

        for th in self.threads:
            th.join()