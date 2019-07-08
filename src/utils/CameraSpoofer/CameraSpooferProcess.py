import os
import cv2
import glob

from threading       import Thread

from src.utils.Templates.WorkerProcess import WorkerProcess

class CameraSpooferProcess(WorkerProcess):

    #================================ INIT ===============================================
    def __init__(self, inPs,outPs, videoDir, ext = '.h264'):
        """Processed used for spoofing a camera/ publishing a video stream from a folder 
        with videos
        
        Arguments:
            inPs {list(Pipe)} -- []
            outPs {list(Pipe)} -- list of output pipes(order does not matter)
            videoDir {str} -- path to a dir with videos 
        """
        WorkerProcess.__init__(self, inPs, outPs)

        # params
        self.mode = 1
        self.videoSize = (640,480)
        
        self.videoDir = videoDir
        self.videos = self.open_files(self.videoDir, ext = ext)

    
    # ===================================== INIT VIDEOS ==================================
    def open_files(self, inputDir, ext):
        "Open all files with the given path and extension"
        
        files =  glob.glob(inputDir + '/*' + ext)  
        
        return files

    # ===================================== INIT THREADS =================================
    def _init_threads(self):
        thPlay = None

        if self.mode == 1:
            thPlay = Thread(target= self.play_video, args=(self.videos, ))
            self.threads.append(thPlay)


    # ===================================== PLAY VIDEO ===================================
    def play_video(self, videos):
        """Iterate through each video in the folder, open a cap and publish the frames.
        
        Arguments:
            videos {[type]} -- [description]
        """
        while True:
            for video in videos:
                cap         =   cv2.VideoCapture(video)
                
                while True:
                    ret, frame = cap.read()
                    if ret: 
                        frame = cv2.resize(frame, self.videoSize)
                        
                        for p in self.outPs:
                            p.send(frame)   
                    else:
                        break

                cap.release()

