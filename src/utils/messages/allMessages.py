from enum import Enum
class mainCamera(Enum): 
    Queue= "General"
    From = "processCamera"
    msgID = 1
    msgType  = "numpyArray"

class serialCamera(Enum): 
    Queue= "General"
    From = "processCamera"
    msgID = 2
    msgType  = "b64encode"
