class messageHandlerSender:
    """Class which will handle sender functionalities.\n
    Args:
        queuesList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        message (enum): A specific message
    """
        
    def __init__(self, queuesList, message):
        self.queuesList = queuesList
        self.message = message

    def send(self, value):
        """
        Puts a value into the queuesList

        Args:
            value (any type): The value to be put into the queue. This can be of any type
        """
        self.queuesList[self.message.Queue.value].put(
            {
                "Owner": self.message.Owner.value,
                "msgID": self.message.msgID.value,
                "msgType": self.message.msgType.value,
                "msgValue": value
            }
        )