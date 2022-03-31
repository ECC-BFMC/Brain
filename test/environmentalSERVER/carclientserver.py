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


import json
import threading
import socketserver
import socket
import time

from env_inf_server.server.utils import load_private_key, load_public_key, sign_data, verify_data

class CarClientServerThread(threading.Thread):
    
    def __init__(self, serverConfig, logger, keyfile, markerSet, clientkeys):
        """ It's a thread to run the server for serving the car clients. By function 'stop' can terminate the client serving.
        """
        super(CarClientServerThread,self).__init__()
        self.carclientserver = CarClientServer(serverConfig, CarClientHandler, logger, keyfile, markerSet, clientkeys)
        self.carclientserver.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        self.carclientserver.serve_forever()
    
    def stop(self):
        self.carclientserver.shutdown()



class CarClientServer (socketserver.ThreadingTCPServer, object):
    """ It has role to serve the car client as a data collector for information about obstacles. It's a subclass of 'SocketServer.ThreadingTCPServer',
    so it creates a new thread for communicating the client. The server use a private key for authentication itself and another one for authenticating the client
    . It stores the data about obstacles in the data_saver object. The identification number of car 
    is equal with id of Aruco marker placed on robot. The client requests are handled by objects of 'CarClientHandler' class. 
    
    """
    def __init__(self, serverConfig, requestHandler, logger, keyfile, markerSet, clientkeys):
        # This map contains the last recorded data
        self.private_key = load_private_key(keyfile)
        self.client_keys_path = clientkeys
        #: contains the last received coordination fo the carId.
        self._markerSet = markerSet
        self.logger = logger

        #: shutdown mechanism
        self.isRunning = True
        # initialize the connection parameters
        connection = (serverConfig.localip, serverConfig.carClientPort)
        super(CarClientServer,self).__init__(connection, requestHandler)
    
    def savePosition(self, id, obs, x, y):
        """Check the existence of robot in dictionary. It returns false, if the robot wasn't detected yet. 
        
        Parameters
        ----------
        id : int
            id number of robot
        
        Returns
        -------
        boolean
        """
        try:
            return self._markerSet.saveitem(id, obs, x, y)
        except:
            return None
    
    def shutdown(self):
        self.isRunning = False
        super(CarClientServer,self).shutdown()

class CarClientHandler(socketserver.BaseRequestHandler):
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
        data = self.request.recv(1024)
        carId = int(data.decode())
        
        # receiving signature from the client
        signature = self.request.recv(4096)
        
        # Each participating team will have a unique ID to connect to the server. The public keys made available by the students to the 
        # organizers will be stored i the key folder, with the corresponding id.
 
        client_key_public_path = self.server.client_keys_path + str(carId) + "_publickey.pem"
        try:
            client_key_public = load_public_key(client_key_public_path)
        except:
            msg = 'Client ' + str(carId) + ' trying to connect. no key available.'
            raise Exception(msg)
        
        # verifying the client authentication
        is_signature_correct = verify_data(client_key_public, data, signature)
        
        # Validate client
        if (data == '' or signature == '' or not is_signature_correct):
            msg = "cannot approve client."
            raise Exception(msg)

        # Authentication
        timestamp = time.time()
        msg_s = "Conneted! " + str(timestamp)
        msg = msg_s.encode('utf-8')
        signature = sign_data(self.server.private_key, msg)
        
        # Authentication of server        
        self.request.sendall(msg)
        self.request.sendall(signature)
        time.sleep(0.1)
        
        # receiving ok response from the client
        msg = self.request.recv(4096)
        
        if  msg.decode('utf-8') != 'Authentication ok':
            raise Exception("Authentication broken")
        
        self.server.logger.info('Connecting with {}. CarId is {}'.format(self.client_address, carId))
        
        try:
            while(self.server.isRunning):
                msg = self.request.recv(4096).decode('utf-8')
                if(msg == ''):
                    self.server.logger.info('Invalid message. Connection interrupted.')
                    break
                received = json.loads(msg)

                self.server.savePosition(carId, received['OBS'], received['x'], received['y'])
                
        except Exception as e:
            self.server.logger.warning("Close serving for {}. Error: {}".format(self.client_address,e))