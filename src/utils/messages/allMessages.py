from enum import Enum

####################################### processCamera #######################################
class mainCamera(Enum): 
    Queue= "General"
    Owner = "processCamera"
    msgID = 1
    msgType  = "numpyArray"

class serialCamera(Enum): 
    Queue= "General"
    Owner = "processCamera"
    msgID = 2
    msgType  = "base64"


################################# processCarsAndSemaphores ##################################
class Cars(Enum):
    Queue = "General"
    Owner = "processCarsAndSemaphores"
    msgID = 1
    msgType = "Position"

class Semaphores(Enum):
    Queue = "General"
    Owner = "processCarsAndSemaphores"
    msgID = 2
    msgType = "State&Position"

################################# From PC ##################################
class EngineRun(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 1
    msgType = "EngineFlag"

class SpeedMotor(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 2
    msgType = "Speed"

class SteerMotor(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 3
    msgType = "SteerAngle"

class control(Enum):
    Queue = "General"
    Owner = "PC"
    msgID = 4
    msgType = "Tasks"

################################# From Nucleo ##################################
class BatteryLvl(Enum):
    Queue = "General"
    Owner = "threadReadSerial"
    msgID = 1
    msgType = "BatteryLVL"

class ImuData(Enum):
    Queue = "General"
    Owner = "threadReadSerial"
    msgID = 2
    msgType = "IMUData"

class InstantConsumption(Enum):
    Queue = "General"
    Owner = "threadReadSerial"
    msgID = 3
    msgType = "Consumption"