import os
import copy

class RcBrainConfigParams:
    def __init__(self,maxSteerAngle,maxSpeed,steerAngleStep,speedStep):
        self.maxSteerAngle = maxSteerAngle
        self.maxSpeed = maxSpeed
        self.steerAngleStep = steerAngleStep
        self.speedStep = speedStep

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
        self.limit_configParam = RcBrainConfigParams(21.0,30.0,3.0,4.0)

        self.startSpeed         =   9.0
        self.startSteerAngle    =   1.0

        #----------------- DEFAULT VALUES ----------------------
        #when the RC is reset, this are the default values
        self.default_configParam = RcBrainConfigParams(20.5,20.0,1.5,2.0)
        
        #----------------- PARAMETERS -------------------------
        #this parameter can be modofied via RC
        self.configParam = copy.deepcopy(self.default_configParam)  

        #----------------- DIRECTION SIGNALS STATES -----------
        self.currentState =[False,False,False,False,False]            #UP, DOWN , LEFT, RIGHT, BRAKE

    # ===================================== DISPLAY INFO =================================
    def displayInfo(self):
        """Display all parameters on the screen. 
        """
        # clear stdout for a smoother display
        os.system('cls' if os.name=='nt' else 'clear')

        print("=========== REMOTE CONTROL ============")
        print(
            "speed:          "  + str(self.speed) +                     '[W/S]' +
            "\nangle:         " + str(self.steerAngle) +                '[A/D]' +
            "\nmaxSpeed :     " + str(self.configParam.maxSpeed) +      '[T/G]' +
            "\nmaxSteerAngle: " + str(self.configParam.maxSteerAngle) + '[Y/H]' +
            "\nacceleration:  " + str(self.configParam.speedStep) +     '[U/J]' +
            "\nsteerStep:     " + str(self.configParam.steerAngleStep) +'[I/K]' +
            '\nReset Params:                                     [ R ]' +
            '\nCtrl+C to exit'
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
        if self.currentState[4]:
            data['action']        =  'BRAK'
        else:
            data['action']        =  'MCTL'
            data['speed']         =  float(self.speed)
        data['steerAngle']    =  float(self.steerAngle)
        print(data)
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

    # If we keep the two buttons pressed the each states are active and the reached value remains constant.
    # When each two keys are released, it sets to zero the value??? to rapid reseting.
    def _updateSpeed(self):
        """Update the speed based on the current state and the keyboard event.
        """
        if self.currentState[4]:
            self.currentState[0] = False
            self.currentState[1] = False
            self.speed = 0
            return
        
        #forward
        if self.currentState[0]:
            if self.speed == 0:
                self.speed = self.startSpeed
            elif self.speed == -self.startSpeed:
                self.speed = 0
            elif self.speed < self.configParam.maxSpeed:
                if  self.configParam.maxSpeed - self.speed < self.configParam.speedStep:
                    self.speed = self.configParam.maxSpeed
                else:
                    self.speed += self.configParam.speedStep
        #backwards
        elif self.currentState[1]:
            if self.speed == 0:
                self.speed = - self.startSpeed
            elif self.speed == self.startSpeed:
                self.speed = 0
            elif self.speed >  -self.configParam.maxSpeed:
                if  abs(self.configParam.maxSpeed + self.speed) < self.configParam.speedStep:
                    self.speed = - self.configParam.maxSpeed
                else:
                    self.speed -= self.configParam.speedStep
        # else:
        #     self.speed = 0.0

    # ===================================== UPDATE STEER ANGLE ===========================
    def _updateSteerAngle(self):
        """Update the steering angle based on the current state and the keyboard event.
        """
        #left steer
        if self.currentState[2] == True:
            if self.steerAngle == 0:
                self.steerAngle = -self.startSteerAngle
            elif self.steerAngle > -self.configParam.maxSteerAngle:
                if self.configParam.maxSteerAngle + self.steerAngle < self.configParam.steerAngleStep:
                    self.steerAngle = - self.configParam.maxSteerAngle
                else:
                    self.steerAngle -= self.configParam.steerAngleStep 
        elif not self.currentState[2] and not self.currentState[3]:
                self.steerAngle = 0
        #right steer    
        if self.currentState[3] == True:
            if self.steerAngle == 0:
                self.steerAngle = self.startSteerAngle
            elif self.steerAngle < self.configParam.maxSteerAngle:
                if self.configParam.maxSteerAngle - self.steerAngle < self.configParam.steerAngleStep:
                    self.steerAngle = self.configParam.maxSteerAngle
                else:
                    self.steerAngle += self.configParam.steerAngleStep
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
            self.configParam = copy.deepcopy(self.default_configParam)  
        #--------------- MAX SPEED ------------------------------
        elif currentKey == 'p.t':
            if self.configParam.maxSpeed < self.limit_configParam.maxSpeed:
                self.configParam.maxSpeed += self.parameterIncrement
        elif currentKey == 'p.g':
            if self.startSpeed < self.configParam.maxSpeed:
                self.configParam.maxSpeed  -= self.parameterIncrement
        #--------------- MAX STEER ANGLE ------------------------
        elif currentKey == 'p.y':
            if self.configParam.maxSteerAngle < self.limit_configParam.maxSteerAngle:
                self.configParam.maxSteerAngle += self.parameterIncrement
        elif currentKey == 'p.h':
            if self.startSteerAngle < self.configParam.maxSteerAngle:
                self.configParam.maxSteerAngle -= self.parameterIncrement
        #--------------- SPEED STEP ------------------------------
        elif currentKey == 'p.u':
            if self.configParam.speedStep < self.limit_configParam.speedStep:
                self.configParam.speedStep += self.parameterIncrement
        elif currentKey == 'p.j':
            if 0.1 < self.configParam.speedStep:
                self.configParam.speedStep -= self.parameterIncrement
        #--------------- STEER STEP ------------------------------
        elif currentKey == 'p.i':
            if self.configParam.steerAngleStep < self.limit_configParam.steerAngleStep:
                self.configParam.steerAngleStep += self.parameterIncrement
        elif currentKey == 'p.k':
            if 0.1 < self.configParam.steerAngleStep:
                self.configParam.steerAngleStep -= self.parameterIncrement
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
        elif currentKey == 'p.space':
            self.currentState[4] = True
        elif currentKey == 'r.space':
            self.currentState[4] = False

        
