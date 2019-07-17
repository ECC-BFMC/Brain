class MessageConverter:
    """Creates the message to be sent over the serial communication

    Allowed commands are represented in the field "command".
    Each key of the dictionary represent a command. Each command has a list of attributes ,
    a list of attributes types and optionally if enhanced precision is to be used(send more 
    digits after the decimal point).

    Example:
        
        'Command' : [ [ arg1 ,  arg2 ],   [type1, type2],  [ enhanced precision] ]
           'MCTL' : [ ['f_vel','f_angle'],[float, float],           [True]  ]
    """

    commands = {
                'MCTL' : [ ['f_vel','f_angle'],[float, float],  [False]  ],
                'BRAK' : [ ['f_angle' ],       [float],         [False] ],
                'PIDA' : [ ['activate'],       [ bool],         [False] ],
                'SFBR' : [ ['activate'],       [ bool],         [False] ],
                'DSPB' : [ ['activate'],       [ bool],         [False] ],
                'ENPG' : [ ['activate'],       [ bool],         [False] ],

                # optional commands
                'PIDS' : [ ['kp','ki','kd','tf'],[ float, float, float, float], [True] ],
                'SPLN' : [ ['A','B','C','D', 'dur_sec', 'isForward'], 
                           [complex, complex, complex, complex, float, bool], [False] ],
            }   

    # ===================================== GET COMMAND ===================================
    def get_command(self, action, **kwargs):
        self.verify_command(action, kwargs)
        
        enhPrec = MessageConverter.commands[action][2][0]
        listKwargs = MessageConverter.commands[action][0]

        command = '#' + action + ':'

        for key in listKwargs:
            value = kwargs.get(key)
            valType = type(value)

            if valType == int:
                command += '{0:d};'.format(value)
            elif valType == float:
                if enhPrec:
                    command += '{0:.5f};'.format(value)
                else:
                    command += '{0:.2f};'.format(value)
            elif valType == complex:
                command += '{0:.2f};{1:.2f};'.format(value.real, value.imag)   
            elif valType == bool:
                command += '{0:d};'.format(value)   
                         
        command += ';\r\n'
        return command

    # ===================================== VERIFY COMMAND ===============================
    def verify_command(self, action, commandDict):
        
        assert len(commandDict.keys()) == len(MessageConverter.commands[action][0]), \
                'Number of arguments does not match'
        for i, [key, value] in enumerate(commandDict.items()):
            assert key in MessageConverter.commands[action][0], \
                    action + "should not contain key:" + key
            assert type(value) == MessageConverter.commands[action][1][i], \
                    action + "should be of type " + \
                    str(MessageConverter.commands[action][1][i]) + 'instead of' + \
                    str(type(value))


if __name__ == "__main__":
    a = MessageConverter()

    com = a.get_command("MCTL", f_angle=0.0, f_vel=0.2 )
    print(com)