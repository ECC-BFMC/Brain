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
from threading import Thread
import time


class PositionListener(Thread):
	"""PositionListener simulator aims to populate position variable. 
	"""
	def __init__(self):

		self.coor = None

		self.__running = True

		self.i=1
		self.j=1

		Thread.__init__(self) 

    ## Method for starting position listener simulation process.
    #  @param self          The object pointer.
	def start(self):
		self.__running = True

		super(PositionListener,self).start()

    ## Method for stopping position listener simulation process.
    #  @param self          The object pointer.
	def stop(self):
		self.__running = False
		
    ## Method for running position listener simulation process.
    #  @param self          The object pointer.
	def run(self):
		""" 
		Update coordiantes every 0.1 seconds
		"""
		while self.__running:
			# Generate some coordinates
			self.i = self.i + 2
			self.j = self.j + 3
			self.coor = (complex(self.i,self.j),complex(self.i+5,self.j+5))

			# Wait for 0.1 s before next adv
			time.sleep(0.1)