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

import time
import threading
from multiprocessing import Pipe
import json
from complexDealer import ComplexEncoder
import socket
import socketserver


class LocalizationDevice(threading.Thread):
    """ It aims to generate coordinates for server. The object of this class simulates
    the detection of robots on the race track. Object of this class calculate the position of robots, 
    when they are executing a circle movement.
    """ 

    def __init__(self, deviceConfig):
        super(LocalizationDevice,self).__init__()
        self.carclientserver = LocalizationDeviceServer(deviceConfig, ConnectionHandler)
        self.carclientserver.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        self.carclientserver.serve_forever()
    
    def stop(self):
        self.carclientserver.shutdown()

        self.__running = True
    
class LocalizationDeviceServer (socketserver.ThreadingTCPServer, object):

    def __init__(self, deviceConfig, ConnectionHandlerr):
        #: shutdown mechanism
        self.isRunning = True
        # initialize the connection parameters
        connection = (deviceConfig["ip"], deviceConfig["port"])
        super(LocalizationDeviceServer,self).__init__(connection, ConnectionHandlerr)
    
    def shutdown(self):
        self.isRunning = False
        super(LocalizationDeviceServer,self).shutdown()


class ConnectionHandler(socketserver.BaseRequestHandler):

    def setup(self):
        self.__r = complex(1.0,0.0)
        self.__circleCenter = complex(0,0)
        self.__angularPosition = complex(1.0,0.0)
        self.__angularVelocity = complex(0.9848, 0.1736)

    def handle(self):
        while self.server.__running:
            # calculating the position of robot
            position = self.__circleCenter+self.__r * self.__angularPosition

            car = {'timestamp':time.time(), 'pos':position}
            msg = json.dumps((car), cls=ComplexEncoder)

            self.request.sendall(msg)

            self.__angularPosition *= self.__angularVelocity
            time.sleep(0.1)

