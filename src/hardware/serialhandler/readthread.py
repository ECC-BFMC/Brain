# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

from src.templates.threadwithstop import ThreadWithStop

class ReadThread(ThreadWithStop):
    def __init__(self,f_serialCon,f_logFile):
        """ The role of this thread is to receive the messages from the micro-controller and to redirectionate them to the other processes or modules. 
        
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

    def subscribe(self, subscribing, f_key, outP):
        """Subscribe a connection to specified response from the other device in order to check the delivery of the messages or feedback form car.. 
        
        Parameters
        ----------
        subscribing : bool
            bool variable for subscribing or unsubscribing
        f_key : string
            the key word, which identify the source of the response 
        outP : multiprocessing.Connection
            The sender connection object, which represent the sending end of pipe. 
        """
        if subscribing:
            if f_key in self.__subscribers:
                if outP in self.__subscribers[f_key]:
                    raise ValueError("%s pipe has already subscribed the %s command."%(outP,f_key))
                else:
                    self.__subscribers[f_key].append(outP)
            else:
                self.__subscribers[f_key] = [outP]
        else:
            if f_key in self.__subscribers:
                if outP in self.__subscribers[f_key]:
                    self.__subscribers[f_key].remove(outP)
                else:
                    raise ValueError("pipe %s wasn't subscribed to key %s"%(outP,f_key))
            else:
                raise ValueError("doesn't exist any subscriber with key %s"%(f_key))    
