from src.utils.templates.threadwithstop import ThreadWithStop


class ReadThread(ThreadWithStop):
    def __init__(self,f_serialCon,f_logFile):
        """ The role of this thread is to receive the messages from the micro-controller and to redirectionate to the other processes or modules. 
        
        Parameters
        ----------
        f_serialCon : serial.Serial
           The serial connection between the two device. 
        f_logFile : FileHandler
            The log file handler object for saving the received messages.
        """
        super(ReadThread,self).__init__()
        self.serialCon=f_serialCon
        self.logFile=f_logFile
        self.buff=""
        self.isResponse=False
        self.__subscribers={}
    
    def run(self):
        """ It's represent the activity of the read thread, to read the messages.
        """
        
        while(self._running):
            read_chr=self.serialCon.read()
            try:
                read_chr=(read_chr.decode("ascii"))
                if read_chr=='@':
                    self.isResponse=True
                    if len(self.buff)!=0:
                        self.__checkSubscriber(self.buff)
                    self.buff=""
                elif read_chr=='\r':   
                    self.isResponse=False
                    if len(self.buff)!=0:
                        self.__checkSubscriber(self.buff)
                    self.buff=""
                if self.isResponse:
                    self.buff+=read_chr
                self.logFile.write(read_chr)
                 
            except UnicodeDecodeError:
                pass

    def __checkSubscriber(self,f_response):
        """ Checking the list of the waiting object to redirectionate the message to them. 
        
        Parameters
        ----------
        f_response : string
            The response received from the other device without the key. 
        """
        l_key=f_response[1:5]
        if l_key in self.__subscribers:
            subscribers = self.__subscribers[l_key]
            for outP in subscribers:
                outP.send(f_response)

    def subscribe(self,f_key,outP):
        """Subscribe a connection to specified response from the other device. 
        
        Parameters
        ----------
        f_key : string
            the key word, which identify the source of the response 
        outP : multiprocessing.Connection
            The sender connection object, which represent the sending end of pipe. 
        """
        if f_key in self.__subscribers:
            if outP in self.__subscribers[f_key]:
                raise ValueError("%s pipe has already subscribed the %s command."%(outP,f_key))
            else:
                self.__subscribers[f_key].append(outP)
        else:
            self.__subscribers[f_key] = [outP]

    def unsubscribe(self,f_key,outP):
        """Unsubscribe a connection from the specified response type 
        
        Parameters
        ----------
        f_key : string
            The key word, which identify the source of the response 
        outP : multiprocessing.Connection
            The sender connection object, which represent the sending end of pipe.
        """
        if f_key in self.__subscribers:
            if outP in self.__subscribers[f_key]:
                self.__subscribers[f_key].remove(outP)
            else:
                raise ValueError("pipe %s wasn't subscribed to key %s"%(outP,f_key))
        else:
            raise ValueError("doesn't exist any subscriber with key %s"%(f_key))    