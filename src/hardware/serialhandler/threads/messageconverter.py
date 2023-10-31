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

        | 'Command' : [ [ arg_list ],                [type_list],                    [enhanced precision]   ]
        | 'SPED'    : [ ['f_vel'],                   [float],                        [False]                ] - Speed command -
        | 'STER'    : [ ['f_angle'],                 [float],                        [False]                ] - Steer command -
        | 'BRAK'    : [ ['f_angle' ],                [float],                        [False]                ] - Brake command -
        | 'ENBL'    : [ ['activate' ],               [bool],                         [False]                ] - Activate batterylevel -
        | 'ENIS'    : [ ['activate' ],               [bool],                         [False]                ] - Activate instant consumption -
        | 'ENIMU'   : [ ['activate' ],               [bool],                         [False]                ] - Activate IMU -
        | 'BEZIER   : [ ["point1x","point1y",        [float, float,                                         ]
        |                "point2x","point2y",         float, float,                                         ]
        |                "point3x","point3y",         float, float,                                         ]
        |  MOVEMENT'     "point4x","point4y",]        float, float]                  [False]                ]
        | 'STS '    : [ ["speed", "time", "steer"]   [float, float, float]           [False]                 ] - Set a speed a timer and a steering angle -

    """

    commands = {
        "1": [["speed"], [float], [False]],
        "2": [["steerAngle"], [float], [False]],
        "3": [["steerAngle"], [float], [False]],
        "5": [["activate"], [bool], [False]],
        "6": [["activate"], [bool], [False]],
        "7": [["activate"], [bool], [False]],
        "8": [
            [
                "point1x",
                "point1y",
                "point2x",
                "point2y",
                "point3x",
                "point3y",
                "point4x",
                "point4y",
            ],
            [float, float, float, float, float, float, float, float],
            [False],
        ],
        "9": [["speed", "time", "steer"], [float, float, float], [False]],
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
        self.verify_command(action, kwargs)

        enhPrec = MessageConverter.commands[action][2][0]
        listKwargs = MessageConverter.commands[action][0]

        command = "#" + action + ":"

        for key in listKwargs:
            value = kwargs.get(key)
            valType = type(value)

            if valType == float:
                if enhPrec:
                    command += "{0:.6f};".format(value)
                else:
                    command += "{0:.2f};".format(value)
            elif valType == bool:
                command += "{0:d};".format(value)

        command += ";\r\n"
        return command

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

        assert len(commandDict.keys()) == len(
            MessageConverter.commands[action][0]
        ), "Number of arguments does not match"
        for i, [key, value] in enumerate(commandDict.items()):
            assert key in MessageConverter.commands[action][0], (
                action + "should not contain key:" + key
            )
            assert type(value) == MessageConverter.commands[action][1][i], (
                action
                + "should be of type "
                + str(MessageConverter.commands[action][1][i])
                + "instead of"
                + str(type(value))
            )
