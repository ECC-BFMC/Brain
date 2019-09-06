from src.utils.templates.workerprocess import WorkerProcess
from threading import Thread

class Consumer(WorkerProcess):
    def __init__(self, inPs, outPs):
        """[summary]
        
        Parameters
        ----------
        inPs : list(Pipe)
            List of the input pipes
        outPs : list(Pipe)
            List of the output pipes
        """
        super(Consumer,self).__init__( inPs, outPs)

    def _init_threads(self):
        """Initialize the threads by adding a consume method for each input pipes. 
        """
        for pipe in self.inPs:
            self.threads.append(Thread(name='Consume',target=Consumer._consume, args=(pipe,)))
    
    @staticmethod
    def _consume(pipe):
        """A simple method to read the content from the input pipe to consume the content of the connection. 
        
        Parameters
        ----------
        pipe : Pipe
            Input communication channel.
        """
        while True:
            res = pipe.recv()
            # print("type recv", type(res))

    
    