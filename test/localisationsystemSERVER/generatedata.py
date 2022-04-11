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

import time
import threading
from multiprocessing import Pipe

from complexDealer import ComplexEncoder
import json

class GenerateData(threading.Thread):
    """ It aims to generate coordinates for server. The object of this class simulates
    the detection of robots on the race track. Object of this class calculate the position and 
    orientation of robots, when they are executing a circle movement. It calculates the same coordinates 
    for 40 robot on the race track. So car client can subscribe on a car id number between 1 and 40. 
    """ 

    def __init__(self, markerdataset = {}, r = 1.0):
        super(GenerateData,self).__init__()
        #: circle radius
        self.__r = complex(1.0,0.0)
        #: circle center
        self.__circleCenter = complex(0,0)
        #: current angular position based on circle center
        self.__angularPosition = complex(1.0,0.0)
        #: angular velocity (angular/second) based on circle center
        self.__angularVelocity = complex(0.9848, 0.1736)

        self._streamPipe = {}
        self._readPipe = {}
        self.locker = threading.Lock()

        self.__running = True
        
        #: inferior value of car id number
        self.__startCarid = 1
        #: superior value of car id number
        self.__endCarid = 40
    
    def run(self):
        """ Actualize the car client server data with the new coordinates. 
        """

        while self.__running:
            # waiting a period
            time.sleep(0.25)
            # calculating the position of robot
            position = self.__circleCenter+self.__r * self.__angularPosition
            # calculation the orientation of robot.
            orientation = self.__angularPosition*complex(0.0, 1.0)

            with self.locker:
                for id in self._streamPipe:
                    for pipe in self._streamPipe[id]:
                        msg = {'timestamp':time.time(), 'coor':(position, orientation)}
                        self._streamPipe[id][pipe].send(msg)  
            # update angular position
            self.__angularPosition *= self.__angularVelocity

    def getPipe(self, id, tme):
        """Creates a pipe for the client.
        Parameters
        ----------
        id : int
            Id of car
        tme : float 
            the time of detectection
        Returns
        -------
        Pipe: pipe receiving side
        """
        with self.locker:
            if not id in self._readPipe:
                self._readPipe[id]   = {}
                self._streamPipe[id] = {}

            gpsStR, gpsStS = Pipe(duplex = False)
            self._readPipe[id][tme]   = gpsStR
            self._streamPipe[id][tme] = gpsStS

            return self._readPipe[id][tme]


    def removePipeS(self):
        """Deletes the pipe for the client.
        Parameters
        ----------
        id : int
            Id of car
        tme : float 
            the time of detectection
        """

        with self.locker:
            for markerId in self._readPipe:
                for timestamp in self._readPipe[markerId]:
                    del self._readPipe[markerId][timestamp]
                    del self._streamPipe[markerId][timestamp]

    def stop(self):
        self.removePipeS()
        self.__running = False
    