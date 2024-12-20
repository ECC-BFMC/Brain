from src.templates.threadwithstop import ThreadWithStop
from src.utils.messages.allMessages import (SpeedMotor, Ultra, mainCamera)
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender
class threadDecisionMaker(ThreadWithStop):
    """This thread handles decisionMaker.
    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
        debugging (bool, optional): A flag for debugging. Defaults to False.
    """

    def __init__(self, queueList, logging, debugging=False):
        self.queuesList = queueList
        self.logging = logging
        self.debugging = debugging
        self.subscribers = {}
        self.speedSender = messageHandlerSender(self.queuesList, SpeedMotor)
        self.subscribe()
        super(threadDecisionMaker, self).__init__()

    def run(self):
        while self._running:
            ultraVals = self.subscribers["Ultra"].receive()
            if ultraVals is not None:
                if ultraVals["top"] < 30:
                    self.speedSender.send(0) #stop the vehicle if front distance is less than 30 cm 
            

    def subscribe(self):
        """Subscribes to the messages you are interested in"""
        subscriber = messageHandlerSubscriber(self.queuesList, Ultra, "lastOnly", True)
        self.subscribers["Ultra"] = subscriber
