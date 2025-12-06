import time  # added this

from src.templates.threadwithstop import ThreadWithStop
from src.utils.messages.allMessages import (mainCamera)
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender

class threadhelloWorld(ThreadWithStop):
    """This thread handles helloWorld.
    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
        debugging (bool, optional): A flag for debugging. Defaults to False.
    """

    def __init__(self, queueList, logging, debugging=False):
        self.queuesList = queueList
        self.logging = logging
        self.debugging = debugging
        
        self.subscribe()
        
        super(threadhelloWorld, self).__init__()

    def subscribe(self):
        """Subscribes to the messages you are interested in"""
                # For now we don't actually subscribe to anything,
        # just log once at startup so we know it's alive.
        self.logging.info("[helloWorld] subscribe() called - no message subscriptions yet")

        # Example of how you'd subscribe to camera messages later:
        # self.cameraSubscriber = messageHandlerSubscriber(
        #     self.queuesList, mainCamera, "lastOnly", True
        # )

    def state_change_handler(self):
        pass

    def thread_work(self):
        """Main periodic work – called repeatedly by ThreadWithStop."""
        try:
            self.logging.info("[helloWorld] heartbeat from helloWorld thread")
        except Exception as e:
            self.logging.error(f"[helloWorld] error in thread_work: {e}")

        # Slow the loop down a bit so logs are readable
        time.sleep(1.0)

