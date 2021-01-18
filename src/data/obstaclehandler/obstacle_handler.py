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
import server_data
import server_listener
import server_subscriber
import obstacle_streamer

import time
import random

class ObstacleHandler(threading.Thread):
    
    def __init__(self, ID):
        """ ObstacleHandler targets to connect on the server and to send messages, which incorporates 
        the coordinate of the encountered obstacles on the race track. It has two main state, the setup state and the streaming state. 
        In the setup state, it creates the connection with server. It's sending the messages to the server in the streaming
        state. 

        It's a thread, so can be run parallel with other threads. You can write the coordinates and the id of the encountered obstacle 
        and the script will send it.

        """
        super(ObstacleHandler, self).__init__()
        #: serverData object with server parameters
        self.__server_data = server_data.ServerData()
        #: discover the parameters of server
        self.__server_listener = server_listener.ServerListener(self.__server_data)
        #: connect to the server
        self.__subscriber = server_subscriber.ServerSubscriber(self.__server_data,ID)
        #: receive and decode the messages from the server
        self.__obstacle_streamer = obstacle_streamer.ObstacleStreamer(self.__server_data)
        
        self.__running = True

    def setup(self):
        """Actualize the server's data and create a new socket with it.
        """
        # Running while it has a valid connection with the server
        while(self.__server_data.socket == None and self.__running):
            # discover the parameters of server
            self.__server_listener.find()
            if self.__server_data.is_new_server and self.__running:
                # connect to the server 
                self.__subscriber.subscribe()
        
    
    def stream(self, obstacle_id, x, y):
        """ Listening the coordination of robot
        """
        ob_id=obstacle_id
        self.__obstacle_streamer.stream(ob_id, x, y)

    def send(self, obstacle_id, x, y):
        try:
            self.__obstacle_streamer.sent = False
            while self.__obstacle_streamer.sent == False and self.__running:
                self.setup()
                self.stream(obstacle_id, x, y)
            return "sent: "
        except:
            return "not returned: "

    def ID(self):
        return self.__subscriber.ID()
    
    def stop(self):
        """Terminate the thread running.
        """
        self.__running = False
        self.__server_listener.stop()
        self.__obstacle_streamer.stop()

if __name__ == '__main__':
    obsthandler = ObstacleHandler(120)
    obsthandler.start()
    for x in range(1, 10):
        try:
            res = obsthandler.send(int(random.uniform(0,25)), random.uniform(0,15), random.uniform(0,15))
            print(res)
        except: pass
        time.sleep(random.uniform(1,5))
    obsthandler.stop()

    obsthandler.join()
