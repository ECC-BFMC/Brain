from src.utils.Templates.WorkerProcess import WorkerProcess

import threading
from threading import Thread

class Consumer(WorkerProcess):
    def __init__(self, inPs, outPs):
        WorkerProcess.__init__(self, inPs, outPs)

    def init_threads(self):
        for pipe in self.inPs:
            self.threads.append(Thread(target=self._consume, args=(pipe,)))
    
    def _consume(self, pipe):
        while True:
            res = pipe.recv()
            print("type recv", type(res))