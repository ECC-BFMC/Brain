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
import threading
from src.templates.threadwithstop import ThreadWithStop
from src.utils.messages.allMessages import BatteryLvl,ImuData,InstantConsumption

class threadRead(ThreadWithStop):
    # ===================================== INIT =========================================
    def __init__(self,f_serialCon,f_logFile,queueList):
        super(threadRead,self).__init__()
        self.serialCon=f_serialCon
        self.logFile=f_logFile
        self.buff=""
        self.isResponse=False
        self.queuesList=queueList
        self.acumulator=0
        self.Queue_Sending()

    # ====================================== RUN ==========================================
    def run(self):
        while(self._running):
            read_chr=self.serialCon.read()
            try:
                read_chr=read_chr.decode("ascii")
                if read_chr=='@':
                    self.isResponse=True
                    if len(self.buff)!=0:
                        self.sendqueue(self.buff)
                    self.buff=""
                elif read_chr=='\r':   
                    self.isResponse=False
                    if len(self.buff)!=0:
                        self.sendqueue(self.buff)
                    self.buff=""
                if self.isResponse:
                    self.buff+=read_chr        
            except UnicodeDecodeError:
                pass
    # ==================================== SENDING =======================================
    def Queue_Sending(self):
        self.queuesList["General"].put({ "Owner" : "processSerialHandler" , "msgID": 1, "msgType" :"Boolean","msgValue":True})
        threading.Timer(1, self.Queue_Sending).start()
        
    def sendqueue(self, buff):
        if buff[0] == 1 :
            print(buff[2:-2])
        elif buff[0] == 2 :
            print(buff[2:-2])
        elif buff[0] == 3 :
            print(buff[2:-2])
        elif buff[0] == 4 :
            print(buff[2:-2])
        elif buff[0] == 5 :
            self.queuesList[BatteryLvl.Queue].put({ "Owner" : BatteryLvl.Owner , "msgID": BatteryLvl.msgID, "msgType" :BatteryLvl.msgType,"msgValue":int(buff[2:-3])})
        elif buff[0] == 6 :
            self.queuesList[InstantConsumption.Queue].put({ "Owner" : InstantConsumption.Owner , "msgID": InstantConsumption.msgID, "msgType" :InstantConsumption.msgType,"msgValue":int(buff[2:-3])})
        elif buff[0] == 7: 
            buff = buff[2:-2]
            splitedBuffer = buff.split(";")
            data={"roll":splitedBuffer[0],"pitch": splitedBuffer[1],"yaw":splitedBuffer[2],"accelx":splitedBuffer[3],"accely":splitedBuffer[4],"accelz":splitedBuffer[5]}
            self.queuesList[ImuData.Queue].put({ "Owner" : ImuData.Owner , "msgID": ImuData.msgID, "msgType" :ImuData.msgType,"msgValue":data})



