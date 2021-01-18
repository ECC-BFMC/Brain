#
#  ******************************************************************************
#  * @file     Listener.py
#  * @author   RBRO/PJ-IU
#  * @version  V0.0.1
#  * @date     13-01-2020 GMOIS
#  * @brief    This file contains the class definition for the listener thread
#  *           on the car.
#  ******************************************************************************
#

# Module imports
import time,sys
import math
from threading import Thread
# Module used for communication
import socket
import os
import sys
import json


class listener(Thread):
    
    
    def __init__(self):
        """listener class. 
        
        Class used for running port listener algorithm 
        """
        
        #: Flag indincating thread state
        self.RUN_LISTENER = False
        
        # Communication parameters, create and bind socket
        self.PORT = 50007
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #(internet, UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.bind(('', self.PORT))

        # Semaphore states
        #: Semaphore at intersection
        self.s1_state=0 
        #: Semaphore at intersection on opposite direction, same as S1
        self.s2_state=0 # 
        #: Start semaphore
        self.s3_state=0 

        #: Semaphore colors
        self.colors = ['red','yellow','green']

        # Debug msg
        print("Created listener ")

        Thread.__init__(self) 

    def run(self):
        """ Method for running listener algorithm.
        """
        # Listen for incomming broadcast messages
        while self.RUN_LISTENER:
            # Wait for data
            try:
                data, addr = self.sock.recvfrom(4096) # buffer size is 1024 bytes

                # Extract ID from message, andupdate corresponding semaphore state
                # Message format
                # Message is an object of type bytes and consists of two bytes
                # Byte 1 - semaphore ID
                # Byte 2 - semaphore state - 0 - RED
                #                          - 1 - YELLOW
                #                          - 2 - GREEN
                dat = data.decode('utf-8')
                dat = json.loads(dat)
                ID = int(dat['id'])
                state = int(dat['state'])
                if (ID == 1):
                    self.s1_state=state
                elif (ID == 2):
                    self.s2_state=state
                elif (ID == 3):
                    self.s3_state=state

            except Exception as e:
                print("Receiving data failed with error: " + str(e))

    def start(self):
        """Method for starting listener process.
        """
        self.RUN_LISTENER = True
        # Debug msg
        print("Started listener ")

        super(listener,self).start()

    def stop(self):
        """ Method for stopping listener process.
        """
        self.RUN_LISTENER = False

    def get_S1(self):
        """Method for getting S1 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s1_state


    def get_S2(self):
        """Method for getting S2 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s2_state


    def get_S3(self):
        """Method for getting S3 state.
        
        Returns
        -------
        int 
            Semaphore state (0 - red, 1 - yellow, 2 - green)
        """
        return self.s3_state
