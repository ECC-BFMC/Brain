if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")

from src.templates.workerprocess import WorkerProcess
from src.utils.helloWorld.threads.threadhelloWorld import threadhelloWorld

class processhelloWorld(WorkerProcess):
    """This process handles helloWorld.
    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
        debugging (bool, optional): A flag for debugging. Defaults to False.
    """

    def __init__(self, queueList, logging, ready_event=None, debugging=False):
        self.queuesList = queueList
        self.logging = logging
        self.debugging = debugging
        super(processhelloWorld, self).__init__(self.queuesList, ready_event)

    def state_change_handler(self):
        pass

    def process_work(self):
        pass

    def _init_threads(self):
        """Create the helloWorld Publisher thread and add to the list of threads."""
        helloWorldTh = threadhelloWorld(
            self.queuesList, self.logging, self.debugging
        )
        self.threads.append(helloWorldTh)
