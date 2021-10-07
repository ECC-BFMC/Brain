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
sys.path.insert(0,'.')

import socket
import json
from complexdecoder import ComplexDecoder



class PositionListener:
	"""PositionListener aims to receive all message from the server. 
	"""
	def __init__(self,server_data):
		
		self.__server_data = server_data 
		self.socket_pos = None

		self.coor = None

		self.__running = True

	def stop(self):
		self.__running = False
	
	def listen(self):
		""" 
		After the subscription on the server, it's listening the messages on the 
		previously initialed socket. It decodes the messages and saves in 'coor'
		member parameter. Each new messages will update this parameter. The server sends 
		result (robot's coordination) of last detection. If the robot was detected by the localization 
		system, the client will receive the same coordinate and timestamp. 
		"""
		while self.__running:
			if self.__server_data.socket != None: 
				try:
					msg = self.__server_data.socket.recv(4096)

					msg = msg.decode('utf-8')
					if(msg == ''):
						print('Invalid message. Connection can be interrupted.')
						break
					
					coor = json.loads((msg),cls=ComplexDecoder)
					self.coor = coor
				except socket.timeout:
					print("position listener socket_timeout")
					# the socket was created successfully, but it wasn't received any message. Car with id wasn't detected before. 
					pass
				except Exception as e:
					self.__server_data.socket.close()
					self.__server_data.socket = None
					print("Receiving position data from server " + str(self.__server_data.serverip) + " failed with error: " + str(e))
					self.__server_data.serverip = None
					break
		self.__server_data.is_new_server = False
		self.__server_data.socket = None
		self.__server_data.serverip = None