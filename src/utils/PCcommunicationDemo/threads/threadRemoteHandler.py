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
from src.utils.PCcommunicationDemo.threads.connection import FactoryDealer
from src.utils.PCcommunicationDemo.threads.periodics import  PeriodicTask
from twisted.internet import reactor

class threadRemoteHandler(ThreadWithStop):
    # ===================================== INIT =====================================
    def __init__(self, queuesList, logging, pipeRecv, pipeSend):
        super(threadRemoteHandler,self).__init__()
        self.factory = FactoryDealer(queuesList)
        self.reactor = reactor
        self.reactor.listenTCP(5000, self.factory)    
        self.queues = queuesList
        self.logging = logging
        self.pipe = pipeRecv
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "processCamera", "msgID":2,"To":{"receiver": "processPCCommunication","pipe":pipeSend}})
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "processCarsAndSemaphores", "msgID":1,"To":{"receiver": "processPCCommunication","pipe":pipeSend}})
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "processCarsAndSemaphores", "msgID":2,"To":{"receiver": "processPCCommunication","pipe":pipeSend}})
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "processSerialHandler", "msgID":1,"To":{"receiver": "processPCCommunication","pipe":pipeSend}}) 
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "processSerialHandler", "msgID":2,"To":{"receiver": "processPCCommunication","pipe":pipeSend}})  
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "processCamera", "msgID":3,"To":{"receiver": "processPCCommunication","pipe":pipeSend}}) 
        self.queues["Config"].put({'Subscribe/Unsubscribe':1,"Owner": "tcpLocsys", "msgID":1,"To":{"receiver": "processPCCommunication","pipe":pipeSend}})  
        self.task = PeriodicTask(self.factory, 0.001, self.pipe)  # Replace X with the desired number of seconds
        print("before task")

    # ===================================== RUN ======================================
    def run(self):
        self.task.start()
        print("before run")
        self.reactor.run(installSignalHandlers=False)
        print("after run")
        
    # ==================================== STOP ======================================
    def stop(self):
        self.reactor.stop()
        super(threadRemoteHandler,self).stop()
        





