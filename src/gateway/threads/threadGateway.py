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

class threadGateway(ThreadWithStop):
# ===================================== INIT =========================================

    def __init__(self, queueList, logger, debugging):
        super(threadGateway,self).__init__()
        self.logger = logger
        self.debugging = debugging
        self.sendingList = {}
        self.queuesList = queueList
        self.messageApproved=[]

# =================================== SUBSCRIBE ======================================

    def subscribe(self, message):
        #Declaration of variables: 
        From = message['From']
        Id = message['msgID']
        To = message["To"]["receiver"]
        Pipe = message["To"]['pipe']
        print(From,Id,To,Pipe)
        if not From in self.sendingList.keys():
            self.sendingList[From] = {}
        if not Id in self.sendingList[From].keys():
            self.sendingList[From][Id] = {}
        if not To in self.sendingList[From][Id].keys():
            self.sendingList[From][Id][To] = Pipe
        self.messageApproved.append(Id)
        #Debugging( you can comment this):
        if self.debugging: self.printList()

# ================================== UNSUBSCRIBE =====================================

    def unsubscribe(self, message):
        From = message['From']
        Id = message['msgID']
        To = message["To"]["receiver"]

        #We delete the value from Dictionary
        del self.sendingList[From][Id][To]
        self.messageApproved.remove(Id)
        if self.debugging: self.printList()
    
# =================================== SENDING ========================================
      
    def send(self,message):
        From= message['From']
        Id = message['msgID']
        Type = message['msgType']
        Value = message['msgValue']
        if Id in self.messageApproved:
            for element in self.sendingList[From][Id]:
                #We send a dictionary that contain the type of the message and message
                self.sendingList[From][Id][element].send({"Type":Type,"value":Value})
                if self.debugging: self.logger.warning(message) 
                


# ====================================================================================

    #Function for debugging:
    def printList(self):
        self.logger.warning(self.sendingList)

# ==================================== RUN ===========================================

    def run(self):
        while self._running:
            message = None
            #We are using "elif" because we are processing one message at a time.
            #We work with the queues in the priority order( We start from the high priority to low priority)
            if not self.queuesList["Critical"].empty():
                message = self.queuesList["Critical"].get()
            elif not self.queuesList["Warning"].empty():
                message= self.queuesList["Warning"].get()
            elif not self.queuesList["General"].empty():
                message= self.queuesList["General"].get()   
            if message is not None:
                self.send(message)
            if not self.queuesList["Config"].empty():
                message2= self.queuesList["Config"].get()
                if message2['Subscribe/Unsubscribe']==1:
                    self.subscribe(message2)
                else:
                    self.unsubscribe(message2)

#=====================================================================================