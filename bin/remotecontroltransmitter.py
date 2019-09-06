from src.utils.remotecontrol.remotecontroltransmitter import RemoteControlTransmitter
from multiprocessing import Event

# ===================================== MAIN =============================================
if __name__ == "__main__":
    a = RemoteControlTransmitter()
    a.daemon = True
    a.start()
    blocker =Event()
    try:
        blocker.wait() 
    except KeyboardInterrupt:
        print("\nCatching a KeyboardInterruption exception! Shutdown all processes.")