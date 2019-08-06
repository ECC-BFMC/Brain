import io
import cv2
import numpy as np
        
import time
import datetime


import threading

from threading import Thread
from multiprocessing import Process

#================================ CAMERA PROCESS =========================================
class CameraPublisher(Thread):
    
    #================================ CAMERA =============================================
    def __init__(self, outPs):
        """The purpose of this thread is to send the camera images. It is able to record
        videos and save them locally.
        
        Parameters
        ----------
        outPs : list(Pipes)
            the list of pipes were the images will be sent
        """
        Thread.__init__(self)


        # streaming options
        self._stream      =   io.BytesIO()
        
        #output 
        self.outPs         =   outPs

    #================================ INIT CAMERA ========================================
    def _init_camera(self):
        """Init the PiCamera and its parameters
        """
        
        # this how the firmware works.
        # the camera has to be imported here
        from picamera import PiCamera

        # camera
        self.camera = PiCamera()

        # camera settings
        self.camera.resolution      =   (1640,1232)
        self.camera.framerate       =   15

        self.camera.brightness      =   50
        self.camera.shutter_speed   =   12000
        self.camera.contrast        =   0
        self.camera.iso             =   0 # auto
        

        self.imgSize                =   (640, 480)    # the actual image size
        self.recordMode             =   False

    # ===================================== GET STAMP ====================================
    def _get_timestamp(self):
        stamp = time.gmtime()
        res = str(stamp[0])
        for data in stamp[1:6]:
            res += '_' + str(data)  

        return res
    #================================ RUN ================================================
    def run(self):
        """Start sending data through pipe. 
        """
        self._init_camera()
        
        # record mode
        if self.recordMode:
            self.camera.start_recording('picam'+ self._get_timestamp()+'.h264',format='h264')

        self.camera.capture_sequence(
                                    self._streams(), 
                                    use_video_port  =   True, 
                                    format          =   'rgb',
                                    resize          =   self.imgSize)
        # record mode
        if self.recordMode:
            self.camera.stop_recording()
     
    #================================ STREAMS ============================================
    def _streams(self):
        """Stream function that actually published the frames into the pipes. Certain 
        processing(reshape) is done to the image format. 
        """
        i = 0

        while True:
            yield self._stream
            self._stream.seek(0)
            data = self._stream.read()

            # read and reshape from bytes to np.array
            data  = np.frombuffer(data, dtype=np.uint8)
            data  = np.reshape(data, (480, 640, 3))
            stamp = time.time()

            # output image and time stamp
            for outP in self.outPs:
                outP.send([[stamp], data])

            
            self._stream.seek(0)
            self._stream.truncate()


