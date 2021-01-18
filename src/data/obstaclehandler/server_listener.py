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

import socket
import sys
sys.path.insert(0,'.')


class ServerListener: 
	""" ServerListener aims to find the server, it waiting a broadcast message on predefined prot.
	The broadcast message contains a port, where the server listens the car clients. If the message is correct,
	it finishes the listening and a subscriber object tries to connect on server.
	"""



	def __init__(self, server_data):
		#: ServerData object, which contains all parameter of the server.
		self.__server_data = server_data

		self.__running = True


	def stop(self):
		self.__running = False

	def find(self):
		""" 
		It creates a socket with predefined parameters, where it waits the broadcast messages. 
		The broadcast message is a port number, where the server listen the car clients.  
		After receiving a message it converts to integer value. 
		After a successfull conversation it closes the process, which follows the subscription. 
		"""
		
		
		try:
			#: create a datagram socket for intramachine use
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			#: used to associate de socket with a specific network interface and port number
			s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			
			s.bind(('', self.__server_data.beacon_port))

			#: Listen for server broadcast 
			s.settimeout(1)
			
			while (not self.__server_data.is_new_server) and self.__running:
				try:
					# waiting for the beacon.
					# Receive data from the socket. Buffer size = 1500 bytes
					data, server_ip = s.recvfrom(1500, 0)

					# convert the received message
					subscriptionPort = int(data.decode("utf-8"))
					
					# actualize the parameter of server_data with new IP address and communication port
					self.__server_data.serverip = server_ip[0]
					self.__server_data.carSubscriptionPort = subscriptionPort
					# server was found 
					self.__server_data.is_new_server=True
				except socket.timeout as e:
					print("cannot find server")
					# Cannot find the server. Need to repeat the process.
					pass
				except ValueError as e:
					print("Wrong message")
					# Wrong message was received. Need to repeat the process.
					pass

		except Exception as e:
			# Cannot initialize the socket for broadcast message listening or other unexpected error.   
			self.__server_data.serverip = None	# Server is dead
			print ("Error:" + str(e))
		finally:
			s.close()
