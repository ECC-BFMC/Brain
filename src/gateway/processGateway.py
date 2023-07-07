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
from src.templates.workerprocess import WorkerProcess
from src.gateway.threads.threadGateway import threadGateway

class processGateway(WorkerProcess):

# ===================================== INIT ==========================================
    
    def __init__(self, queueList, logger, debugging = False):
        self.logger = logger
        self.debugging = debugging
        super(processGateway,self).__init__(queueList)

# ===================================== STOP ==========================================

    def stop(self):
        for thread in self.threads:
            thread.stop()
            thread.join()
        super(processGateway,self).stop()
    
# ===================================== RUN ===========================================       
    def run(self):
        super(processGateway, self).run()

# ===================================== INIT TH ==========================================
    def _init_threads(self):
        """ Initializes the read and the write thread.
        """
        # read write thread        
        readThread  = threadGateway(self.queuesList, self.logger, self.debugging)
        self.threads.append(readThread)

# =================================== EXAMPLE ========================================= 
#             ++    THIS WILL RUN ONLY IF YOU RUN THE CODE FROM HERE  ++
#                  in terminal:    python3 processGateway.py

if __name__ == "__main__":
    from multiprocessing import Pipe,Queue, Event
    import time
    import logging

    allProcesses = list()
    #We have a list of multiprocessing.Queue() which individualy represent a priority for processes.
    queueList = {"Critical": Queue(),
                 "Warning": Queue(), 
                 "General": Queue(), 
                 "Config": Queue()}
    logging  = logging.getLogger()
    process = processGateway(queueList, logging, debugging=True)
    allProcesses.append(process)

    for process in allProcesses:
        process.daemon = True
        process.start()

    #We have two types of dictionaries that will be send to threadGateway.py
    #   First format is the configDictionary:  -- {Subscribe/Unsubscribe, From, msgID, To{ receiver, pipe}} --
    #       Subscribe/Unsubscribe key let us know which action to take;
    #       From key let us know form who the config dictionary come;
    #       msgID key let us see what message has been send( One process can send messages to multiple components);
    #       To is also a dictionary in which we have two fields: receiver and pipe;
    #           Receiver key represents the component that will receive the message;
    #           Pipe key represents a multiprocessing.Pipe(the way of sending the message).
    #   The second format is the mesageDictionary: -- {From, msgID, msgType, msgValue} --
    #       From key let us know form who the config dictionary come;
    #       msgID key let us know what message has been send( One process can send messages to multiple components);
    #       msgType key let us know what is the type of the message;
    #       msgValue key let us know the value that has to be send.

    pipeReceive1, pipeSend1= Pipe()
    queueList["Config"].put({"Subscribe/Unsubscribe":1, "From":"Camera", "msgID":1, "To": {"receiver":1,"pipe":pipeSend1}})
    time.sleep(1)

    pipeReceive2, pipeSend2= Pipe()
    queueList["Config"].put({"Subscribe/Unsubscribe":1, "From":"Camera", "msgID":2, "To": {"receiver":2,"pipe":pipeSend2}})
    time.sleep(1)

    pipeReceive3, pipeSend3= Pipe()
    queueList["Config"].put({"Subscribe/Unsubscribe":1, "From":"Camera", "msgID":3, "To": {"receiver":3,"pipe":pipeSend3}})
    time.sleep(1)

    queueList["Critical"].put({"From": "Camera", "msgID":1, "msgType":"1111","msgValue":"This is the text1"})

    queueList["Warning"].put({"From": "Camera", "msgID":3, "msgType":"1111","msgValue":"This is the text3"})

    queueList["General"].put({"From": "Camera", "msgID":2, "msgType":"1111","msgValue":"This is the text2"})
    time.sleep(2)

    # Code to verify that the function send from threadGateway.py is working properly.

    print(pipeReceive3.recv())
    print(pipeReceive1.recv())
    print(pipeReceive2.recv())


# ===================================== STAYING ALIVE ====================================
    blocker = Event()  

    try:
        blocker.wait()
    except KeyboardInterrupt:
        print("\nCatching a KeyboardInterruption exception! Shutdown all processes.\n")
        for proc in allProcesses:
            if hasattr(proc,'stop') and callable(getattr(proc,'stop')):
                print("Process with stop",proc)
                proc.stop()
                proc.join()
            else:
                print("Process witouth stop",proc)
                proc.terminate()
                proc.join()
