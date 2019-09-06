from src.utils.camerastreamer.camerareceiver import CameraReceiver
from multiprocessing import Event


# ===================================== MAIN =============================================
if __name__ == "__main__":
    a = CameraReceiver([],[])
    a.start()
    blocker =Event()
    try:
        blocker.wait() 
    except KeyboardInterrupt:
        print("\nCatching a KeyboardInterruption exception! Shutdown all processes.")
        a.terminate()
    a.join()