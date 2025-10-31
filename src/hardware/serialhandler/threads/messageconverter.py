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


class MessageConverter:
    """Creates the message to be sent over the serial communication

    Allowed commands are represented in the field "command".
    Each key of the dictionary represent a command. Each command has a list of attributes ,
    a list of attributes types and optionally if enhanced precision is to be used(send more
    digits after the decimal point).

    Implemented commands:

        | 'Command' : [ [ arg_list ],                [precision in digits            [enhanced precision]   ]
        | 'SPEED'   : [ ['f_vel'],                   [2],                            [False]                ] - Speed command -
        | 'STER'    : [ ['f_angle'],                 [3],                            [False]                ] - Steer command -
        | 'BRAK'    : [ ['f_angle' ],                [int],                          [False]                ] - Brake command -
        | 'BTC'     : [ ['capacity' ],               [int],                          [False]                ] - Set battery capacity -
        | 'ENBL'    : [ ['activate' ],               [int],                          [False]                ] - Activate batterylevel -
        | 'ENIS'    : [ ['activate' ],               [int],                          [False]                ] - Activate instant consumption -
        | 'ENRM'    : [ ['activate' ],               [int],                          [False]                ] - Activate resource monitor -
        | 'ENIMU'   : [ ['activate' ],               [int],                          [False]                ] - Activate IMU -
        | 'STS '    : [ ["speed", "time", "steer"]   [int, int, int]                 [False]                ] - Set a speed a timer and a steering angle -
        | 'KL'      : [ ['f_mode'],                  [int],                          [False]                ] - Enable/Diasble functions -
    """

    commands = {
        "speed": [["speed"], [3], [False]],
        "steer": [["steerAngle"], [3], [False]],
        "brake": [["steerAngle"], [3], [False]],
        "batteryCapacity": [["capacity"], [5], [False]],
        "battery": [["activate"], [1], [False]],
        "instant": [["activate"], [1], [False]],
        "resourceMonitor": [["activate"], [1], [False]],
        "alive": [["activate"], [1], [False]],
        "steerLimits": [["request"], [1], [False]],
        "imu": [["activate"], [1], [False]],
        "vcd": [["speed", "steer", "time"], [3, 3, 3], [False]],
        "vcdCalib": [["speed", "steer", "time"], [3, 3, 3], [False]],
        "kl": [["mode"], [2], [False]]
    }
    """ The 'commands' attribute is a dictionary, which contains key word and the acceptable format for each action type. """

    # ===================================== GET COMMAND ===================================
    def get_command(self, action, **kwargs):
        """This method generates automatically the command string, which will be sent to the other device.

        Parameters
        ----------
        action : string
            The key word of the action, which defines the type of action.
        **kwargs : dict
            Optional keyword parameter, which have to contain all parameters of the action.


        Returns
        -------
        string
            Command with the decoded action, which can be transmite to embed device via serial communication.
        """
        valid = self.verify_command(action, kwargs)
        if valid:
            enhPrec = MessageConverter.commands[action][2][0]
            listKwargs = MessageConverter.commands[action][0]

            command = "#" + action + ":"

            for key in listKwargs:
                value = kwargs.get(key)
                command += str(value)+";"

            command += ";\r\n"
            return command
        else:
            return "error"

    # ===================================== VERIFY COMMAND ===============================
    def verify_command(self, action, commandDict):
        """The purpose of this method to verify the command, the command has the right number and named parameters.

        Parameters
        ----------
        action : string
            The key word of the action.
        commandDict : dict
            The dictionary with the names and values of command parameters, it has to contain all parameters defined in the commands dictionary.
        """
        if len(commandDict.keys()) != len(MessageConverter.commands[action][0]):
            print( "Number of arguments does not match" + str(len(commandDict.keys())), str(len(MessageConverter.commands[action][0])))
            return False
        for i, [key, value] in enumerate(commandDict.items()):
            if key not in MessageConverter.commands[action][0]:
                print(action + " should not contain key: " + key)
                return False
            elif type(value) != int:
                print(action + " should be of type int instead of " + str(type(value)))
                return False
            elif value<0 and len(str(value)) > (MessageConverter.commands[action][1][i]+1):
                print(action + " should have " + str(MessageConverter.commands[action][1][i]) + " digits ")
                return False
            elif value>0 and len(str(value)) > MessageConverter.commands[action][1][i]:
                print(action + " should have " + str(MessageConverter.commands[action][1][i]) + " digits ")
                return False

        return True

