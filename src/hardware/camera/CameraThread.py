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

import io
import numpy as np
import time

from src.templates.threadwithstop import ThreadWithStop

#================================ CAMERA PROCESS =========================================
class CameraThread(ThreadWithStop):
    
    #================================ CAMERA =============================================
    def __init__(self, outPs):
        """The purpose of this thread is to setup the camera parameters and send the result to the CameraProcess. 
        It is able also to record videos and save them locally. You can do so by setting the self.RecordMode = True.
        
        Parameters
        ----------
        outPs : list(Pipes)
            the list of pipes were the images will be sent
        """
        super(CameraThread,self).__init__()
        self.daemon = True


        # streaming options
        self._stream      =   io.BytesIO()

        self.recordMode   =   False
        
        #output 
        self.outPs        =   outPs

    #================================ RUN ================================================
    def run(self):
        """Apply the initializing methods and start the thread. 
        """
        self._init_camera()
        
        # record mode
        if self.recordMode:
            self.camera.start_recording('picam'+ self._get_timestamp()+'.h264',format='h264')

        # Sets a callback function for every unpacked frame
        self.camera.capture_sequence(
                                    self._streams(), 
                                    use_video_port  =   True, 
                                    format          =   'rgb',
                                    resize          =   self.imgSize)
        # record mode
        if self.recordMode:
            self.camera.stop_recording()
     

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
        self.camera.shutter_speed   =   1200
        self.camera.contrast        =   0
        self.camera.iso             =   0 # auto
        

        self.imgSize                =   (640, 480)    # the actual image size

    # ===================================== GET STAMP ====================================
    def _get_timestamp(self):
        stamp = time.gmtime()
        res = str(stamp[0])
        for data in stamp[1:6]:
            res += '_' + str(data)  

        return res

    #================================ STREAMS ============================================
    def _streams(self):
        """Stream function that actually published the frames into the pipes. Certain 
        processing(reshape) is done to the image format. 
        """

        while self._running:
            
            yield self._stream
            self._stream.seek(0)
            data = self._stream.read()

            # read and reshape from bytes to np.array
            data  = np.frombuffer(data, dtype=np.uint8)
            data  = np.reshape(data, (480, 640, 3))
            stamp = time.time()

            # output image and time stamp
            # Note: The sending process can be blocked, when doesn't exist any consumer process and it reaches the limit size.
            for outP in self.outPs:
                outP.send([[stamp], data])

            
            self._stream.seek(0)
            self._stream.truncate()


