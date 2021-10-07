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

"""ServerData class contains all parameter of server. It need to connect to the server.
The parameters is updated by other class, like ServerListener and SubscribeToServer
"""
class ServerData:

	def __init__(self, server_IP = None, beacon_port = 23456):
		#: ip address of server 
		self.__server_ip = server_IP 
		#: flag to mark, that the server is new. It becomes false, when the client subscribed on the server.
		self.is_new_server = False
		#: port, where the beacon server send broadcast messages
		self.__beacon_port = beacon_port
		#: port, where the server listen the car clients
		self.carSubscriptionPort = None
		#: connection, which used to communicate with the server
		self.socket = None

	
	@property
	def beacon_port(self):
		return self.__beacon_port

	@property
	def serverip(self):
		return self.__server_ip

	@serverip.setter
	def serverip(self, server_ip):
		if self.__server_ip != server_ip:
			self.__server_ip = server_ip
			self.is_new_server = True
	
