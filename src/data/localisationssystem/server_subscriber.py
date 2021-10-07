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

import sys
import time
from cryptography.utils import signature
sys.path.insert(0,'.')
import traceback

import socket

from utils import load_public_key,verify_data

class ServerSubscriber:
	""" It has role to subscribe on the server, to create a connection and verify the server authentication.
	It uses the parameter of server_data for creating a connection. After creating it sends the identification number
	of robot and receives two message to authorize the server. For authentication it bases on the public key of server. This 
	key is stored in 'publickey.pem' file.
	"""
	def __init__(self, server_data, carId):
		#: id number of the robot
		self.__carId = carId
		#: object with server parameters
		self.__server_data = server_data
		#: public key of the server for authentication
		#: for testing purposes, with the provided simulated localisation system, use the "publickey_server_test.pem"
		#: At Bosch location, during the competition and during the testing on the track, please use the "publickey_server.pem"
# 		self.__public_key = load_public_key('publickey_server.pem')
		self.__public_key = load_public_key('publickey_server_test.pem')

	def ID(self):
		return self.__carId

	def subscribe(self): 
		""" 
		It connects to the server and send the car id. After sending the car identification number it checks the server authentication.
		"""
		try:
			# creating and initializing the socket
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect((self.__server_data.serverip,self.__server_data.carSubscriptionPort ))
			sock.settimeout(2.0)
			
			# sending car id to the server
			if(sys.version_info[0] < 3 ): #Compatible with python 2 or 3
				msg = bytes("{}".format(self.__carId)).encode('utf-8')
			else:
				msg = "{}".format(self.__carId).encode('utf-8')
			
			sock.sendall(msg)
			
			# receiving response from the server
			msg = sock.recv(4096).decode('utf-8')
			# receiving signature from the server
			signature = sock.recv(4096)
			
			# verifying server authentication
			is_signature_correct = verify_data(self.__public_key,msg,signature)
			
			# Validate server
			if (msg == '' or signature == '' or not is_signature_correct):
				msg = "Authentication not ok".encode('utf-8')
				sock.sendall(msg)
				raise Exception("Authentication failed")
			
			msg = "Authentication ok".encode('utf-8')
			
			sock.sendall(msg)
			 
			print("Connected to ",self.__server_data.serverip)
			self.__server_data.socket = sock
			self.__server_data.is_new_server = False
		
		except Exception as e:
			print("Failed to connect on server with error: " + str(e))
			time.sleep(1)
			self.__server_data.is_new_server = False
			self.__server_data.socket = None
			self.__server_data.serverip = None

		