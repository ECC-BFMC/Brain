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
import socketserver
import socket
import time

from utils import load_private_key, sign_data

class CarClientServerThread(threading.Thread):
    
    def __init__(self, serverConfig, logger, keyfile, devices):
        """ It's a thread to run the server for serving the car clients. By function 'stop' can terminate the client serving.
        """
        super(CarClientServerThread,self).__init__()
        self.carclientserver = CarClientServer(serverConfig, CarClientHandler, logger, keyfile, devices)
        self.carclientserver.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        self.carclientserver.serve_forever()
    
    def stop(self):
        self.carclientserver.shutdown()



class CarClientServer (socketserver.ThreadingTCPServer, object):
    """ It's a subclass of 'SocketServer.ThreadingTCPServer', so it creates a new thread for communicating with each new client. 
    The server use a private key for authentication itself. After the server is authenticated, it shares with the client car the ip and port of the desiredlocalisation device. 
    """
    def __init__(self, serverConfig, requestHandler, logger, keyfile, devices):
        # This map contains the last recorded data
        self.private_key = load_private_key(keyfile)
        self.devices = devices

        self.logger = logger

        #: shutdown mechanism
        self.isRunning = True
        # initialize the connection parameters
        connection = (serverConfig.localip, serverConfig.carClientPort)
        self.allow_reuse_address = True
        super(CarClientServer,self).__init__(connection, requestHandler)   
    
    def shutdown(self):
        self.isRunning = False
        self.server_close()
        super(CarClientServer,self).shutdown()

class CarClientHandler(socketserver.BaseRequestHandler):
    """CarClientHandler responds for a client. 
    Firstly it requests a identification number of the localisation device from the car client.
    Then, information related this id  will be sent to client, together with a crypted message, which will help validate the authenticity of the server.
    The client then confirms the server is valid.
    The server sends the ip and connection port of the device to the client, which will then close the communication with the server.
    The car client will connect to the localisation device.

    Parameters
    ----------
    SocketServer : [type]
        [description]
    """

    def handle(self):
        # receiving car id from client 
        gpsId = int(self.request.recv(1024).decode())
        
        # Authentication
        timestamp = time.time()
        msg_s = "Conneted! " + str(timestamp)
        msg = msg_s.encode('utf-8')
        signature = sign_data(self.server.private_key, msg)
        
        # Authentication of server        
        self.request.sendall(msg)
        time.sleep(0.1)
        self.request.sendall(signature)
        
        # receiving ok response from the client
        msg = self.request.recv(4096)
        
        if  msg.decode('utf-8') != 'Authentication ok':
            raise Exception("Authentication broken")
        
        self.server.logger.info('Connecting client {}. with gps {}'.format(self.client_address, gpsId))
        # Sending the coordinates for car client
        try:
            msg_s = self.server.devices[gpsId]["ip"] + ":" + str(self.server.devices[gpsId]["port"])
            msg = msg_s.encode('utf-8')
            self.request.sendall(msg)
        except:
            msg_s = "gpsId not ok"
            msg = msg_s.encode('utf-8')
            self.request.sendall(msg)