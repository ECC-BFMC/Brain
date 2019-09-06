#========================================================================
# SCRIPT USED FOR WIRING ALL COMPONENTS
#========================================================================
import sys
sys.path.append('.')

import time
import signal
from multiprocessing import Pipe, Process, Event 

# hardware imports
from src.hardware.camera.cameraprocess               import CameraProcess
from src.hardware.serialhandler.serialhandler        import SerialHandler

# data imports
# from src.data.GpsProcess.GpsProcess              import GpsProcess
# from src.data.consumer.consumerprocess             import Consumer

# utility imports
from src.utils.camerastreamer.camerastreamer       import CameraStreamer
from src.utils.cameraspoofer.cameraspooferprocess  import CameraSpooferProcess
from src.utils.remotecontrol.remotecontrolreceiver import RemoteControlReceiver

# =============================== CONFIG =================================================
enableStream        =  True
enableCameraSpoof   =  False 
enableRc            =  True
#================================ PIPES ==================================================


# gpsBrR, gpsBrS = Pipe(duplex = False)           # gps     ->  brain
#================================ PROCESSES ==============================================
allProcesses = list()

# =============================== HARDWARE PROCC =========================================
# ------------------- camera + streamer ----------------------
if enableStream:
    camStR, camStS = Pipe(duplex = False)           # camera  ->  streamer

    if enableCameraSpoof:
        camSpoofer = CameraSpooferProcess([],[camStS],'vid')
        allProcesses.append(camSpoofer)

    else:
        camProc = CameraProcess([],[camStS])
        allProcesses.append(camProc)

    streamProc = CameraStreamer([camStR], [])
    allProcesses.append(streamProc)





# =============================== DATA ===================================================
#gps client process
# gpsProc = GpsProcess([], [gpsBrS])
# allProcesses.append(gpsProc)



# ===================================== CONTROL ==========================================
#------------------- remote controller -----------------------
if enableRc:
    rcShR, rcShS   = Pipe(duplex = False)           # rc      ->  serial handler

    # serial handler process
    shProc = SerialHandler([rcShR], [])
    allProcesses.append(shProc)

    rcProc = RemoteControlReceiver([],[rcShS])
    allProcesses.append(rcProc)

print("Starting the processes!",allProcesses)
for proc in allProcesses:
    proc.daemon = True
    proc.start()

blocker = Event()  

try:
    blocker.wait()
except KeyboardInterrupt:
    print("\nCatching a KeyboardInterruption exception! Shutdown all processes.\n")
    for proc in allProcesses:
        if hasattr(proc,'stop') and callable(getattr(proc,'stop')):
            print("Process with stop",proc)
            proc.stop()
            proc.join()
        else:
            print("Process witouth stop",proc)
            proc.terminate()
            proc.join()
