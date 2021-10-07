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

from serverconfig import ServerConfig
from carclientserver import CarClientServerThread
from serverbeacon import ServerBeaconThread
from data_saver import DataSaver

import logging
import time

class ObstacleHandlerSystemServer:
    """ObstacleHandlerSystemServer aims to serve the car clients by receiving the sent coordinates and the obstacle id encountered on the map. 
    It involves a ServerConfig object, CarClientServerThread object, ServerBeaconThread object. 
    The object of ServerConfig accumulates all information about server. The object of ServerBeaconThread 
    aims to infrom the client about the server ip by sending continuously a broadcast message. The object of 
    CarClientServerThread are serving the car clients. 
    In this examples, a object of GenerateData is added for create coordinates of a robots, which are moving on circle.
    """
    def __init__(self,logger):
        self.serverconfig = ServerConfig('<broadcast>',23456,23466)
        self.data_saver = DataSaver()
        
        self.__carclientserverThread = CarClientServerThread(self.serverconfig, self.data_saver, logger)
        self.__beaconserverThread =  ServerBeaconThread(self.serverconfig,1.0,logger)
     
    def run(self):    
        self.__carclientserverThread.start()
        self.__beaconserverThread.start()
 
        try:
            while(True):
                time.sleep(2.0)
        except KeyboardInterrupt:
            pass
             
        self.__carclientserverThread.stop()
        self.__carclientserverThread.join()
        self.__beaconserverThread.stop()
        self.__beaconserverThread.join()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('root')
    ObsHanServer = ObstacleHandlerSystemServer(logger)
    ObsHanServer.run()