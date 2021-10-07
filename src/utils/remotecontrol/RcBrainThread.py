# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
import os
import copy

class RcBrainConfigParams:
    def __init__(self,maxSteerAngle,maxSpeed,steerAngleStep,speedStep, kpStep, kiStep, kdStep):
        """ The aim of the class is to group the configuration parameters for the rcBrain. 
        
        Parameters
        ----------
        maxSteerAngle : float
            Maximum value of steering angle
        maxSpeed : float
            Maximum value of speed
        steerAngleStep : float
            The step value of steering angle
        speedStep : [type]
            The step value of speed
        """
        self.maxSteerAngle = maxSteerAngle
        self.maxSpeed = maxSpeed
        self.steerAngleStep = steerAngleStep
        self.speedStep = speedStep
        self.kpStep = kpStep
        self.kiStep = kiStep
        self.kdStep = kdStep

class RcBrainThread:
    
    # ===================================== INIT =========================================
    def __init__(self):
        """It's an example to process the keyboard events and convert them to commands for the robot.
        """

        self.speed = 0.0
        self.steerAngle = 0.0
        self.pida = False
        self.pids_kp = 0.115000
        self.pids_ki = 0.810000
        self.pids_kd = 0.000222
        self.pids_tf = 0.040000

        #----------------- CONSTANT VALUES --------------------
        #this values do not change
        self.parameterIncrement =   0.1
        self.limit_configParam = RcBrainConfigParams(21.0, 30.0, 3.0, 4.0, 0.001, 0.001, 0.000001)

        self.startSpeed         =   9.0
        self.startSteerAngle    =   1.0

        #----------------- DEFAULT VALUES ----------------------
        #when the RC is reset, this are the default values
        self.default_configParam = RcBrainConfigParams(20.5,20.0,1.5,2.0, 0.001, 0.001, 0.000001)
        
        #----------------- PARAMETERS -------------------------
        #this parameter can be modified via key events. 
        self.configParam = copy.deepcopy(self.default_configParam)  

        #----------------- DIRECTION SIGNALS STATES -----------
        self.currentState =[False,False,False,False,False, False, False, False]   #UP, DOWN , LEFT, RIGHT, BRAKE, PIDActive, PIDSvalues, SteerRelease

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
            "\npid:           " + str(self.pida) +                      '[P]'   +
            "\npid KP:        " + str(self.pids_kp) +                   '[Z/X]' +
            "\npid KI:        " + str(self.pids_ki) +                   '[V/B]' +
            "\npid KD:        " + str(self.pids_kd) +                   '[N/M]' +
            "\nmaxSpeed :     " + str(self.configParam.maxSpeed) +      '[T/G]' +
            "\nmaxSteerAngle: " + str(self.configParam.maxSteerAngle) + '[Y/H]' +
            "\nacceleration:  " + str(self.configParam.speedStep) +     '[U/J]' +
            "\nsteerStep:     " + str(self.configParam.steerAngleStep) +'[I/K]' +
            '\nReset Params:                                             [ R ]' +
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
            data['steerAngle']    =  float(self.steerAngle)
        elif self.currentState[0] or self.currentState[1]:
            data['action']        =  'SPED'
            data['speed']         =  float(self.speed/100.0)
        elif self.currentState[2] or self.currentState[3]:
            data['action']        =  'STER'
            data['steerAngle']    =  float(self.steerAngle)
        elif self.currentState[5]:
            data['action']        =  'PIDA'
            data['activate']      =  self.pida
            self.currentState[5]  = False
        elif self.currentState[6]:
            data['action']        =  'PIDS'
            data['kp']      =  self.pids_kp
            data['ki']      =  self.pids_ki
            data['kd']      =  self.pids_kd
            data['tf']      =  self.pids_tf
            self.currentState[6]  = False
        elif self.currentState[7]:
            data['action']        =  'STER'
            data['steerAngle']    =  0.0
            self.currentState[7] = False
        else:
            return None
            
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
        self._updatePID(data)
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


    def _updatePID(self, currentKey):
        """Update the parameter of the PID values.
        
        Parameters
        ----------
        currentKey : string
            Keyboard event encoded in string.
        """      
        #--------------- ACTIVATE/DEACTIVATE PID ------------------------------
        if currentKey == 'p.p':
            self.pida = not self.pida
            self.currentState[5] = True

        #--------------- KP PID ------------------------------
        elif currentKey == 'p.z':
            self.pids_kp += self.configParam.kpStep
            self.currentState[6] = True
        elif currentKey == 'p.x':
            self.pids_kp -= self.configParam.kpStep
            self.currentState[6] = True

        #--------------- KI PID ------------------------------
        elif currentKey == 'p.v':
            self.pids_ki += self.configParam.kiStep
            self.currentState[6] = True
        elif currentKey == 'p.b':
            self.pids_ki -= self.configParam.kiStep
            self.currentState[6] = True

        #--------------- KD PID ------------------------------
        elif currentKey == 'p.n':
            self.pids_kd += self.configParam.kdStep
            self.currentState[6] = True
        elif currentKey == 'p.m':
            self.pids_kd -= self.configParam.kdStep
            self.currentState[6] = True

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
            self.currentState[7] = True
        elif currentKey == 'p.d':
            self.currentState[3] = True
        elif currentKey == 'r.d':
            self.currentState[3] = False
            self.currentState[7] = True
        elif currentKey == 'p.space':
            self.currentState[4] = True
        elif currentKey == 'r.space':
            self.currentState[4] = False

        
