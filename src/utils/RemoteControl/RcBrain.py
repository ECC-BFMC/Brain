import os

class RcBrain:
    
    # ===================================== INIT =========================================
    def __init__(self):
        """It's an example to process the keyboard events and convert them to commands for the robot.
        """

        self.speed = 0.0
        self.steerAngle = 0.0

        #----------------- CONSTANT VALUES --------------------
        #this values do not change
        self.parameterIncrement =   0.1      
        self.maxSteerAngle      =   21.0
        self.maxSpeed           =   30.0
        self.maxSpeedStep       =   3.0
        self.maxSteerAngleStep  =   4.0

        self.startSpeed         =   9.0
        self.startSteerAngle    =   1.0

        #----------------- DEFAULT VALUES ----------------------
        #when the RC is reset, this are the default values
        self.maxSpeedDefault        =   20.5
        self.maxSteerAngleDefault   =   20
        self.speedStepDefault       =   1.5
        self.steerStepDefault       =   2.0
        
        #----------------- PARAMETERS -------------------------
        #this parameter can be modofied via RC
        self.speedStepParam     =   self.speedStepDefault       #acceleration
        self.steerStepParam     =   self.steerStepDefault       #steering speed
        self.maxSpeedParam      =   self.maxSpeedDefault        #max allowed speed
        self.maxSteerAngleParam =   self.maxSteerAngleDefault   

        #----------------- DIRECTION SIGNALS STATES -----------
        self.currentState =[False,False,False,False]            #UP, DOWN , LEFT, RIGHT

    # ===================================== DISPLAY INFO =================================
    def displayInfo(self):
        """Display all parameters on the screen. 
        """
        # clear stdout for a smoother display
        os.system('cls' if os.name=='nt' else 'clear')

        print("=========== REMOTE CONTROL ============")
        print(
            "speed:          "  + str(self.speed) +             '[W/S]' +
            "\nangle:         " + str(self.steerAngle) +        '[A/D]' +
            "\nmaxSpeed :     " + str(self.maxSpeedParam) +     '[T/G]' +
            "\nmaxSteerAngle: " + str(self.maxSteerAngleParam) +'[Y/H]' +
            "\nacceleration:  " + str(self.speedStepParam) +    '[U/J]' +
            "\nsteerStep:     " + str(self.steerStepParam) +    '[I/K]' +
            '\nReset Params:                                     [ R ]' 

        )
    # ===================================== STATE DICT ===================================
    def _stateDict(self):
        """It generates a dictionary with the robot current states. 
        
        Returns
        -------
        dict
            It contains the robot current control state, speed and angle. 
        """
        data = {}
        data['controlState']  =  1
        data['speed']         =  self.speed
        data['steerAngle']    =  self.steerAngle

        return data
    # ========================= CALLBACK =================================================
    def getMessage(self,data):
        """ Generate the message based on the current pressed or released key and the current state. 
        
        Parameters
        ----------
        data : string
            The filtered and encoded keyboard event.
        Returns
        -------
        string
            The encoded command.
        """

        self._updateMotionState(data)

        self._updateSpeed()
        self._updateSteerAngle()
        self._updateParameters(data)
        self.displayInfo()
        
        return self._stateDict()        

    # ===================================== UPDATE SPEED =================================
    def _updateSpeed(self):
        """Update the speed based on the current state and the keyboard event.
        """
        #forward
        if self.currentState[0] == True:
            if self.speed == 0:
                self.speed = self.startSpeed
            elif self.speed < self.maxSpeedParam:
                if  self.maxSpeedParam - self.speed < self.speedStepParam:
                    self.speed += self.maxSpeedParam - self.speed
                else:
                    self.speed += self.speedStepParam

        elif not self.currentState[1] and not self.currentState[0]:
                self.speed = 0

        #backwards
        if self.currentState[1] == True:
            if self.speed == 0:
                self.speed = - self.startSpeed
            elif self.speed >  -self.maxSpeedParam:
                if  abs(self.maxSpeedParam + self.speed) < self.speedStepParam:
                    self.speed -= self.maxSpeedParam + self.speed
                else:
                    self.speed -= self.speedStepParam
        elif not self.currentState[1] and not self.currentState[0]:
                self.speed = 0

    # ===================================== UPDATE STEER ANGLE ===========================
    def _updateSteerAngle(self):
        """Update the steering angle based on the current state and the keyboard event.
        """
        #left steer
        if self.currentState[2] == True:
            if self.steerAngle == 0:
                self.steerAngle = -self.startSteerAngle
            elif self.steerAngle > -self.maxSteerAngleParam:
                if self.maxSteerAngleParam + self.steerAngle < self.steerStepParam:
                    self.steerAngle -= self.maxSteerAngleParam + self.steerAngle
                else:
                    self.steerAngle -= self.steerStepParam 
        elif not self.currentState[2] and not self.currentState[3]:
                self.steerAngle = 0
        #right steer    
        if self.currentState[3] == True:
            if self.steerAngle == 0:
                self.steerAngle = self.startSteerAngle
            elif self.steerAngle < self.maxSteerAngleParam:
                if self.maxSteerAngleParam - self.steerAngle < self.steerStepParam:
                    self.steerAngle += self.maxSteerAngleParam - self.steerAngle
                else:
                    self.steerAngle += self.steerStepParam
        elif not self.currentState[2] and not self.currentState[3]:
                self.steerAngle = 0

    # ===================================== UPDATE PARAMS ================================
    def _updateParameters(self, currentKey):
        """Update the parameter of the control mechanism (limits and steps).
        
        Parameters
        ----------
        currentKey : string
            Keyboard event encoded in string.
        """
        #--------------- RESET ---------------------------------
        if currentKey == 'p.r':
            self.speed = 0.0
            self.steerAngle = 0.0
            self.speedStepParam     =   self.speedStepDefault
            self.steerStepParam     =   self.steerStepDefault
            self.maxSpeedParam      =   self.maxSpeedDefault
            self.maxSteerAngleParam =   self.maxSteerAngleDefault   

        #--------------- MAX SPEED ------------------------------
        elif currentKey == 'p.t':
            if self.maxSpeedParam < self.maxSpeed:
                self.maxSpeedParam += self.parameterIncrement
        elif currentKey == 'p.g':
            if self.startSpeed < self.maxSpeedParam:
                self.maxSpeedParam -= self.parameterIncrement
        #--------------- MAX STEER ANGLE ------------------------
        elif currentKey == 'p.y':
            if self.maxSteerAngleParam < self.maxSteerAngle:
                self.maxSteerAngleParam += self.parameterIncrement
        elif currentKey == 'p.h':
            if self.startSteerAngle < self.maxSteerAngleParam:
                self.maxSteerAngleParam -= self.parameterIncrement
        #--------------- SPEED STEP ------------------------------
        elif currentKey == 'p.u':
            if self.speedStepParam < self.maxSpeedStep:
                self.speedStepParam += self.parameterIncrement
        elif currentKey == 'p.j':
            if 0.1 < self.speedStepParam:
                self.speedStepParam -= self.parameterIncrement
        #--------------- STEER STEP ------------------------------
        elif currentKey == 'p.i':
            if self.steerStepParam < self.maxSteerAngleStep:
                self.steerStepParam += self.parameterIncrement
        elif currentKey == 'p.k':
            if 0.1 < self.steerStepParam:
                self.steerStepParam -= self.parameterIncrement
        elif currentKey == 'p.p':
            self.displayInfo()

    # ===================================== UPDATE MOTION STATE ==========================
    def _updateMotionState(self, currentKey):
        """ Update the motion state based on the current state and the pressed or released key. 
        
        Parameters
        ----------
        currentKey : string 
            Encoded keyboard event.
        """
        if currentKey == 'p.w':
            self.currentState[0] = True
        elif currentKey == 'r.w':
            self.currentState[0] = False
        elif currentKey == 'p.s':
            self.currentState[1] = True
        elif currentKey == 'r.s':
            self.currentState[1] = False
        elif currentKey == 'p.a':
            self.currentState[2] = True
        elif currentKey == 'r.a':
            self.currentState[2] = False
        elif currentKey == 'p.d':
            self.currentState[3] = True
        elif currentKey == 'r.d':
            self.currentState[3] = False
        
