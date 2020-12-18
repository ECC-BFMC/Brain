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

from threading import Thread
import socket
import time

##
class ServerBeaconThread(Thread):
	""" This class implementing a thread with a broadcast functionality
	Periodically sends broadcast signalling itself as the server
	"""
	def __init__(self,serverConfig,sleepDuration,logger):
		Thread.__init__(self)
		self.name='ServerBeaconThread'
		self.sleepDuration = sleepDuration
		
		self.serverConfig = serverConfig
		self.runningThread = True
		self.logger = logger

	"""It aims to send a message on broadcast in each period. The message contains the port, where 
	the clients can connect to the server. 
	"""
	def run(self):
		try:
			# Create and setup a socket for broadcasting the server data. 
			beacon = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			beacon.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			beacon.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			beacon.bind(('', self.serverConfig.negotiation_port))
			
			self.logger.info(self.name+' started')
			
			# Sending the message periodically
			msg = bytes(str(self.serverConfig.carClientPort))
			while self.runningThread:
				beacon.sendto( msg , (self.serverConfig.broadcast_ip, self.serverConfig.negotiation_port))
				time.sleep(self.sleepDuration)
			# Close the connection
			beacon.close()

			self.logger.info(self.name+' stoped')
		except Exception as e:
			self.runningThread=False
			self.logger.warning(self.name+' stoped with exception '+str(e))
	## Stop thread.
	#  @param self   The object pointer. 
	def stop(self):
		self.runningThread=False