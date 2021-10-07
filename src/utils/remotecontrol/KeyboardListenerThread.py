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

from pynput import keyboard 
from threading import Thread

class KeyboardListenerThread(Thread):

    # ===================================== INIT =========================================
    def __init__(self, outPs):
        """A thread for capturing the keyboard events. 
        
        Parameters
        ----------
        outPs : list(Pipe)
            List of output pipes.
        """
        super(KeyboardListenerThread,self).__init__()

        self.outPs = outPs

        self.dirKeys   = ['w', 'a', 's', 'd']
        self.paramKeys = ['t','g','y','h','u','j','i','k', 'r', 'p']
        self.pidKeys = ['z','x','v','b','n','m']

        self.allKeys = self.dirKeys + self.paramKeys + self.pidKeys

    # ===================================== START ========================================
    def run(self):
        """ Monitoring the keyboard by utilizing two keyboard listeners callbacks. on_press and on_release
        """
        with keyboard.Listener(
                            on_press   = self.keyPress,
                            on_release = self.keyRelease
                        ) as listener: 

            listener.join()

    # ===================================== KEY PRESS ====================================
    def keyPress(self,key):
        """Processing the key pressing 
        
        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """                                     
        try:                                                
            if key.char in self.allKeys:
                keyMsg = 'p.' + str(key.char)

                for outP in self.outPs:
                    outP.send(keyMsg)
    
        except AttributeError:                              #for special keys (esc,ctrl)    
            if key == keyboard.Key.space:
                key = 'p.space'
                for outP in self.outPs:
                    outP.send(key)          

    # ===================================== KEY RELEASE ==================================
    def keyRelease(self, key):
        """Processing the key realeasing.
        
        Parameters
        ----------
        key : pynput.keyboard.Key
            The key realeased. 
        
        """ 
        if key == keyboard.Key.esc:                        #exit key                   
            return False

        try:                                               
            if key.char in self.allKeys:
                keyMsg = 'r.'+str(key.char)

                for outP in self.outPs:
                    outP.send(keyMsg)
    
        except AttributeError:                              #for special keys (esc,ctrl)    
            if key == keyboard.Key.space:
                keyMsg = 'r.space'
                for outP in self.outPs:
                    outP.send(keyMsg) 
    

