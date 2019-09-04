import threading
from threading import Thread

class WorkerThread(Thread):
    def __init__(self, inPs, outPs):
        """WorkerThread is a template class for a general thread with few input and output pipes. 
        
        Parameters
        ----------
        inPs : list(Pipes)
            input pipes 
        outPs : list(Pipes)
            output pipes 
        """
        super(WorkerThread,self).__init__()
        self.inQs = inQs
        self.outQs = outQs

        self.threads = list()

    
    def _init_threads(self):
        """Initialization of the threads. 
        
        Raises
        ------
        NotImplementedError
            Have to implement the initialization method
        """
        raise NotImplementedError
        
    