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
import cv2
import time
import base64
import picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput

from src.utils.messages.allMessages import mainCamera,serialCamera
from src.templates.threadwithstop import ThreadWithStop

class threadCamera(ThreadWithStop):
    
  #================================ INIT ===============================================
    def __init__(self,queuesList,logger,debugger,recordMode):
        super(threadCamera,self).__init__()
        self.queuesList = queuesList
        self.logger = logger
        self.debugger = debugger
        self.recordMode = recordMode
        self._init_camera()
    
  #=============================== STOP ================================================
    def stop(self):
        super(threadCamera,self).stop()

  #================================ RUN ================================================
    def run(self):
        var=True
        while self._running:
            if self.debugger==True:
                self.logger.warning("getting image")
            request= self.camera.capture_array("main")
            if var:
              request2= self.camera.capture_array("lores") # Will capture an array that can be used by OpenCV library
              request2= request2[:120,:]
              img = cv2.cvtColor(request2, cv2.COLOR_RGB2BGR)
              _, encoded_img = cv2.imencode('.jpg', img)
              image_data_encoded = base64.b64encode(encoded_img).decode('utf-8')
              self.queuesList[serialCamera.Queue.value].put({ "Owner"  :serialCamera.Owner.value , "msgID": serialCamera.msgID.value, "msgType" : serialCamera.msgType.value,"msgValue":image_data_encoded })
            var= not var  
            self.queuesList[mainCamera.Queue.value].put({ "Owner" : mainCamera.Owner.value , "msgID": mainCamera.msgID.value, "msgType" :mainCamera.msgType.value,"msgValue":request })

  #=============================== START ===============================================
    def start(self):
        super(threadCamera,self).start()

  #================================ INIT CAMERA ========================================
    def _init_camera(self):
        self.camera= picamera2.Picamera2()                                                            
        config = self.camera.create_preview_configuration(buffer_count=1,queue=False,main={"format": 'XRGB8888',"size":(1920,1080)},lores ={"size": (200,120)},encode="lores")
        self.camera.configure(config)
        # if we activate the recordMode flag we will be able to get a 5 second video in h264 format of what the camera see
        if self.recordMode:
            video_config =self.camera.create_video_configuration()
            self.camera.configure(video_config)
            encoder = H264Encoder()
            output = CircularOutput()
            self.camera.start_recording(encoder, output)
            output.fileoutput="file.h264"
            output.start()
            time.sleep(5)
            self.camera.stop_recording()
            output.stop()
        self.camera.start()
        
  #=========================== INIT CAMERA CONTROLS ====================================
    def _camera_controls_config(self):
        # If we want to see all the things that we can change in camera_controls
        if self.debugger==True:
            self.logger.warning(self.camera.camera_controls) 
        FrameRate = 30
        frameTime=1000000//FrameRate
        self.camera.set_controls({"FrameDurationLimits":(frameTime,frameTime),"Brightness": 0.1,"Contrast":0.0})


