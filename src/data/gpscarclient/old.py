from threading import Thread
from socket import *
from math import *
from random import *
from time import *
import sys

class GpsClient():
    
    # ===================================== INIT =========================================
    def __init__(self) :
        
        #  ports
        self.negPort        =   12346
        self.carSubPort     =   self.negPort + 2
        self.carCommPort    =   self.negPort + 4


        # car params
        self.thisCarId      =   2
        self.carId          =   self.thisCarId
        self.carPos         =   0+0j
        self.carOrient      =   0+0j

        self.maxWaitTime    =   10
        self.serverIp       =   None
        self.newServerIp    =   False
        self.startUp        =   True
        self.gSocketPos     =   socket()
        self.sentFlag       =   False

    # ===================================== GET SERVER ===================================
    def get_server(self):
        # listen for server broadcast and extract server IP address

        while True:
            try:
                s = socket(AF_INET, SOCK_DGRAM)
                s.bind(('', self.negPort))
                s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

                WAIT_TIME = 2 + floor(10 * self.maxWaitTime * random() ) / 10

                t = time()
                server = []

                # listen for server broadcast
                s.settimeout(WAIT_TIME) 

                data, server_ip = s.recvfrom(1500, 0)
                # new server
                if server_ip[0] != self.serverIp:
                    self.newServerIp  =  True
                    self.serverIp     =   server_ip[0]	# server is alive
                    self.id_to_server()	
                    self.startUp      =   False		
                else:
                    # old server
                    self.newServerIp = False
                    if self.sentFlag == False:
                        self.id_to_server()	
                        print("Subscribe @ GPS server")
                                
                # server beacon received
                s.close()
                
            except Exception as e:
                self.serverIp = None # server is dead

                if  self.startUp == False and \
                    self.serverIp == None and \
                    self.newServerIp == True:
                    
                    self.gSocketPos.close()
                    print("Socket from get position closed!")
                    
                print ("Not connected to server! IP: " + str(self.serverIp) + \
                         "! Error:" + str(e))
                s.close()

    # ===================================== ID_TO_SERVER =================================
    def id_to_server(self):

        try:
            s = socket()         
            # print(self.serverIp)
            print("Vehicle " + str(self.thisCarId) + " subscribing to GPS server: " + \
                     str(self.serverIp) + ':'+str(self.carSubPort))
            
            s.connect((self.serverIp, self.carSubPort))
            sleep(2) 

            car_id_str = str(self.thisCarId)
            s.send(bytes(car_id_str, "UTF-8"))
            s.shutdown(SHUT_WR)
            s.close()

            print("Vehicle ID sent to server----------------------------")
            self.sentFlag = True

        except Exception as e:
            print("Failed to send ID to server, with error: " + str(e))
            s.close()
            self.sentFlag = False

    # ===================================== GET POS  =====================================
    def get_position_thread(self, outPs):

        while True:
            if self.serverIp != None:	# if server alive/valid
                if self.newServerIp == True:
                    try:
                        self.gSocketPos.close()
                    except:
                        pass

                    try:
                        # if there is a GPS server available then open a socket and then wait for GPS data
                        self.gSocketPos = socket()      
                        self.gSocketPos.bind(('', self.carCommPort))   
                        self.gSocketPos.listen(2)		
                    except Exception as e:
                        print("Creating new socket for get position from server: " + \
                                str(self.serverIp) + " with error: "+str(e))
                        return		
                try:
                    c, addr = self.gSocketPos.accept()     
                    data = str(c.recv(4096)) # raw message      
                    # mesage parsing
                    self.carId= int(data.split(';')[0].split(':')[1])
                    if self.carId == self.thisCarId:

                        self.carPos = complex(
                            float(data.split(';')[1].split(':')[1].split('(')[1].split('+')[0]), 
                            float(data.split(';')[1].split(':')[1].split('j')[0].split('+')[1])
                        )

                        self.carOrient = complex(
                                float(data.split(';')[2].split(':')[1].split('(')[1].split('+')[0]), 
                                float(data.split(';')[2].split(':')[1].split('j')[0].split('+')[1])
                            )

                        for outP in outPs:
                            outPs.send((self.carPos, self.carOrient))

                        print("id:" + str(self.carId) + " -position: " + \
                                str(self.carPos) + " -orientation: " + \
                                str(self.carOrient))

                    c.close()

                    
                except Exception as e:
                        print("Receiving position data from server failed! from: " + \
                                str(self.serverIp) + " with error: " + str(e))
                                
                        c.close()