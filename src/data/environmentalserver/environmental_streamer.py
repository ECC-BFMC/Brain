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
import time



class EnvironmentalStreamer:
	
	def __init__(self,server_data):
		"""EnvironmentalStreamer aims to send all message to the server. 
		"""
		
		self.__server_data = server_data 
		self.socket_pos = None
		
		self.sent = False

	def stop(self):
		self.sent = False
		
	def stream(self, obstacle_id, x, y):
		""" 
		After the subscription on the server, it's publishing the messages on the 
		previously initialed socket.
		"""
		if self.__server_data.socket != None: 
			try:
				data = {'OBS': obstacle_id, 'x': x, "y": y}
				msg = json.dumps((data))
				try:
					self.__server_data.socket.sendall(msg.encode('utf-8'))
				except:
					self.__server_data.socket.sendall(msg)
				time.sleep(0.25)
				self.sent = True
			except Exception as e:
				self.__server_data.socket.close()
				self.__server_data.is_new_server = False
				self.__server_data.socket = None
				print("Sending data to server " + str(self.__server_data.serverip) + " failed with error: " + str(e))
				self.__server_data.serverip = None
			finally: 
				pass
			
		else:
			self.__server_data.is_new_server = False
			self.__server_data.socket = None
			self.__server_data.serverip = None