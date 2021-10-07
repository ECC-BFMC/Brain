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

import os
import json
import threading
import SocketServer
import socket
import time
from cryptography.utils import signature

try:
    from server.utils import load_private_key, load_public_key, sign_data, verify_data
except ImportError:
    from utils import load_private_key, load_public_key, sign_data, verify_data


class CarClientServerThread(threading.Thread):
    
    def __init__(self, serverConfig, dataSaver, logger, keyfile = "privatekey_server_test.pem"):
        """ It's a thread to run the server for serving the car clients. By function 'stop' can terminate the client serving.
        """
        super(CarClientServerThread,self).__init__()
        self.carclientserver = CarClientServer(serverConfig, CarClientHandler, dataSaver , logger, keyfile)
        self.carclientserver.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        self.carclientserver.serve_forever()
    
    def stop(self):
        self.carclientserver.shutdown()



class CarClientServer (SocketServer.ThreadingTCPServer, object):
    """ It has role to serve the car client as a data collector for information about obstacles. It's a subclass of 'SocketServer.ThreadingTCPServer',
    so it creates a new thread for communicating the client. The server use a private key for authentication itself and another one for authenticating the client
    . It stores the data about obstacles in the data_saver object. The identification number of car 
    is equal with id of Aruco marker placed on robot. The client requests are handled by objects of 'CarClientHandler' class. 
    
    """
    def __init__(self, serverConfig, requestHandler, dataSaver, logger, keyfile):
        # This map contains the last recorded data
        self.private_key = load_private_key(keyfile)
        #: contains the last received coordination fo the carId.
        self.logger = logger
        self.dataSaver = dataSaver

        #: shutdown mechanism
        self.isRunning = True
        # initialize the connection parameters
        connection = (serverConfig.localip,serverConfig.carClientPort)
        super(CarClientServer,self).__init__(connection,requestHandler)
    
    def shutdown(self):
        self.isRunning = False
        self.dataSaver.saving()
        super(CarClientServer,self).shutdown()

class CarClientHandler(SocketServer.BaseRequestHandler):
    """CarClientHandler responds for a client. Firstly it requests a identification number of robot and the encrypted id. If it validates the robot, it 
    will send a message and a signature, which can help for authenticating the server.
    While the connection is alive and the process isn't stopped.
    
    Parameters
    ----------
    SocketServer : [type]
        [description]
    """

    def handle(self):
        # receiving car id from client 
        data = str(self.request.recv(1024)) 
        self.carId = int(data)
        
        # receiving signature from the client
        signature = self.request.recv(4096)
        
        # Each participating team will have a unique ID to connect to the server. The public keys made available by the students to the 
        # organizers will be stored in the key folder, with the corresponding connection id.
        
        dirname = os.path.dirname(__file__)
        client_key_public_path = dirname + "/keys/" + str(self.carId) + "_publickey.pem"
        try:
            client_key_public = load_public_key(client_key_public_path)
        except:
            msg = 'Client ' + str(self.carId) + ' trying to connect. no key available.'
            raise Exception(msg)
        
        # verifying the client authentication
        is_signature_correct = verify_data(client_key_public, data, signature)
        
        # Validate client
        if (data == '' or signature == '' or not is_signature_correct):
            msg = "cannot approve client."
            raise Exception(msg)

        # Authentication
        timestamp = time.time()
        msg = "Conneted! " + str(timestamp).encode('utf-8')
        signature = sign_data(self.server.private_key,msg)
        
        # Authentication of server        
        self.request.sendall(msg)
        self.request.sendall(signature)
        time.sleep(0.1)
        
        # receiving ok response from the client
        msg = self.request.recv(4096)
        if msg == 'Authentication not ok':
            raise Exception(msg)
        
        self.server.logger.info('Connecting with {}. CarId is {}'.format(self.client_address,self.carId))
        
        try:
            while(self.server.isRunning):
                msg = self.request.recv(4096)
                msg = msg.decode('utf-8')
                if(msg == ''):
                    print('Invalid message. Connection interrupted.')
                    break
                received = json.loads(msg)
                self.server.logger.info('card ID {}. message ID {}. x: {}. y: {}'.format(self.carId, received['OBS'], received['x'], received['y']))
                self.server.dataSaver.ADDobstacle(self.carId, received['OBS'], received['x'], received['y'])
            
            time.sleep(0.25)
                
        except Exception as e:
            self.server.logger.warning("Close serving for {}. Error: {}".format(self.client_address,e))
