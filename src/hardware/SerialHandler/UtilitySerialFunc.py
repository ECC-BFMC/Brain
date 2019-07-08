import threading
import time
import time
# import SerialHandler


def SettingPid(serialHandler, Activate=False):
    ev1 = threading.Event()
    serialHandler.readThread.addWaiter("PIDA", ev1)
    sent = serialHandler.sendPidActivation(Activate)
    if sent:
        isConfirmed = ev1.wait(timeout=3.0)
        if(isConfirmed):
            print("Pid was set successfully to:", Activate)
        else:
            raise ConnectionError('Response', 'Response was not received!')

    else:
        print("Sending problem")
    serialHandler.readThread.deleteWaiter("PIDA", ev1)


def SettingEncoderPub(serialHandler, Activate=False):
    ev1 = threading.Event()
    serialHandler.readThread.addWaiter("ENPB", ev1)
    sent = serialHandler.sendEncoderPublisher(Activate)
    if sent:
        isConfirmed = ev1.wait(timeout=3.0)
        if(isConfirmed):
            print("Encoder publisher was set successfully to:", Activate)
        else:
            raise ConnectionError('Response', 'Response was not received!')

    else:
        print("Sending problem")
    serialHandler.readThread.deleteWaiter("ENPB", ev1)


def sendMove(f_serialHandler, f_forwardSpeed, f_steeringAngle, f_event=None):
    t1 = time.time()
    ev = threading.Event()
    f_serialHandler.readThread.addWaiter("MCTL",ev)
    sentMessage = f_serialHandler.sendMove(f_forwardSpeed, f_steeringAngle)
    if sentMessage:
        isConfirmed = ev.wait(timeout=3.0)
        if(isConfirmed):
            print("Moving was confirmed!")
        else:
            raise ConnectionError('Response', 'Response was not received!')

    else:
        print("Sending problem")
    f_serialHandler.readThread.deleteWaiter("MCTL",ev)
    t2 = time.time()

    print('Response from Nuc',t2-t1)

def sendBrake(f_serialHandler, f_steeringAngle, f_event=None):
    sentMessage = f_serialHandler.sendBrake(f_steeringAngle)
    if sentMessage:
        isConfirmed = False
        nrIndex = 0
        while(not isConfirmed):
            isConfirmed = f_event.wait(timeout=1)
            if(nrIndex > 10):
                break
            nrIndex += 1
        f_event.clear()
        if(isConfirmed):
            print("Braking was confirmed!")
        else:
            raise ConnectionError(
                'Response', 'Response was not received!'+str(nrIndex))

    else:
        print("Sending problem")
