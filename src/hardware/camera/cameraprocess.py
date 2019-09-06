
import multiprocessing
from multiprocessing import Process

from src.utils.templates.workerprocess import WorkerProcess
from src.hardware.camera.camerapublisher import CameraPublisher

class CameraProcess(WorkerProcess):
    #================================ CAMERA PROCESS =====================================
    def __init__(self, inPs, outPs, daemon = True):
        """Process that start the camera streaming.

        Parameters
        ----------
        inPs : list()
            input pipes (leave empty list)
        outPs : list()
            output pipes (order does not matter, output camera image on all pipes)
        daemon : bool, optional
            daemon process flag, by default True
        """
        super(CameraProcess,self).__init__( inPs, outPs, daemon = True)

    # ===================================== INIT TH ======================================
    def _init_threads(self):
        """Create the Camera Publisher thread and add to the list of threads.
        """
        camTh = CameraPublisher(self.outPs) 
        self.threads.append(camTh)
