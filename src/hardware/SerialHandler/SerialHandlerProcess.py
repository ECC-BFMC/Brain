import threading
import multiprocessing

from threading        import  Event, Thread
from multiprocessing  import  Process

from src.hardware.SerialHandler.SerialHandler import *
from src.hardware.SerialHandler import UtilitySerialFunc

from src.utils.Templates.WorkerProcess import WorkerProcess

class SerialHandlerProcess(WorkerProcess):
    #================================ INIT  ==============================================
    def __init__(self, inPs, outPs):
        """Handler for serial communication between Nucleo and Raspberry

            Input pipes:
                1. control message
            
            Output pipes:
                2. encoder output pipes 

        Arguments:
            inPs {list(Pipe)} -- order matters, list of input pipes
            outPs {list(Pipe)} -- list of output pipes, order matters
        """

        Process.__init__(self)

        self.inPs   =   inPs
        self.outPs  =   outPs

        self.serialHandler = SerialHandler()
        self.encoderEvent = Event()

        self.threads = []

    #================================ INIT HANDLER =======================================
    def _init_handler(self):
        """Initialize the Serial handler

                -- enable the PIB
                -- set encoder callback
                -- start the reading thread
                -- enable the encoder callback 
        """
        self.serialHandler.startReadThread()                                              
        UtilitySerialFunc.SettingEncoderPub(self.serialHandler, False) 
        self.serialHandler.sendPidActivation(False)
        self.serialHandler.readThread.addWaiter('ENPB', self.encoderEvent, self._encoder_callback) 

    #================================ INIT THREADS =======================================
    def _init_threads(self):

        controlTh         =  Thread(target=self._control_thread, args=(self.inPs[0], ))
        controlTh.daemon  =  True

        self.threads.append(controlTh)

    #================================ RUN ================================================
    def run(self):
        self._init_handler()
        self._init_threads()

        for th in self.threads:
            th.daemon = True
            th.start()

        for th in self.threads:
            th.join()

    #================================ CONTROL THREAD =====================================
    def _control_thread(self, inP):
        """Send the control comman to Nucleo board.

        The control message is of type dict and has the following keys:
            -- controlState -- [0/1]
            -- speed        -- if PID is activated (give in m/s) else give in percent(0-100)    
            -- steerAngle   -- steering angle  [-23, +23]

        Arguments:
            inP {Pipe} -- control message 
        """
        while True:
            controlMsg = inP.recv()
            # t1 = time.time()

            if controlMsg['controlState']:
                self.serialHandler.sendMove(controlMsg['speed'], controlMsg['steerAngle'])
            else:
                self.serialHandler.sendBrake(controlMsg['steerAngle'])

            # t2 = time.time()

    #================================ ENCODER CALLBACK ===================================
    def _encoder_callback(self, encResp):
        "Publish the message on encoder pipe"                                                 
        try:
            encVal = float(encResp)
            self.outPs[0].send(encVal)                                                    

        except ValueError as e:
            pass