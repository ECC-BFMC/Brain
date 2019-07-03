#========================================================================
# SCRIPT USED FOR WIRING ALL COMPONENTS
#========================================================================
import sys
sys.path.append('.')

import time
from multiprocessing import Pipe, Process

# hardware imports
from src.hardware.Camera.CameraProcess               import CameraProcess
from src.hardware.SerialHandler.SerialHandlerProcess import SerialHandlerProcess

# data imports
# from src.data.GpsProcess.GpsProcess              import GpsProcess
from src.data.Consumer.ConsumerProcess             import Consumer

# utility imports
from src.utils.CameraStreamer.CameraStreamer       import CameraStreamer
from src.utils.CameraSpoofer.CameraSpooferProcess  import CameraSpooferProcess
from src.utils.RemoteControl.RemoteControlReceiver import RemoteControlReceiver

# =============================== CONFIG =================================================
enableStream        =  False
enableCameraSpoof   =  False
enableRc            =  True
#================================ PIPES ==================================================

camStR, camStS = Pipe(duplex = False)           # camera  ->  streamer
gpsBrR, gpsBrS = Pipe(duplex = False)           # gps     ->  brain
rcShR, rcShS   = Pipe(duplex = False)           # rc      ->  serial handler

camCsR, camCsS = Pipe(duplex = False)           # camera  ->  consumer
#================================ PROCESSES ==============================================
allProcesses = list()

# =============================== HARDWARE PROCC =========================================
# ------------------- camera + streamer ----------------------
if enableStream:
    streamProc = CameraStreamer([camStR], [])
    allProcesses.append(streamProc)

    camProc = CameraProcess([],[ camCsS, camStS])
else:
    camProc = CameraProcess([],[camCsS])

allProcesses.append(camProc)


# serial handler process
shProc = SerialHandlerProcess([rcShR], [])
allProcesses.append(shProc)

# =============================== DATA ===================================================
#gps client process
# gpsProc = GpsProcess([], [gpsBrS])
# allProcesses.append(gpsProc)

#consumer process
consProc = Consumer([camCsR], [])
allProcesses.append(consProc)

# ===================================== CONTROL ==========================================
#------------------- remote controller -----------------------
if enableRc:
    rcProc = RemoteControlReceiver([],[rcShS])
    allProcesses.append(rcProc)


for proc in allProcesses:
    proc.daemon = True
    print(proc)
    proc.start()

for proc in allProcesses:
    proc.join()