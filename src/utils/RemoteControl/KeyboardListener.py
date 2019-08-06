import time
from pynput import keyboard 
import sys
from threading import Thread

class KeyboardListener(Thread):

    # ===================================== INIT =========================================
    def __init__(self, outPs):
        """A thread for capturing the keyboard events. 
        
        Parameters
        ----------
        outPs : list(Pipe)
            List of output pipes.
        """
        Thread.__init__(self)

        self.outPs = outPs

        self.dirKeys   = ['w', 'a', 's', 'd']
        self.paramKeys = ['t','g','y','h','u','j','i','k', 'r', 'p']

        self.allKeys = self.dirKeys + self.paramKeys

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
            if key == keyboard.Key.esckeyboard.Key.esc:
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
    
    # ===================================== START ========================================
    def run(self):
        """Monitoring the keyboard by utilizing a keyboard.Listener
        """
        with keyboard.Listener(
                            on_press   = self.keyPress,
                            on_release = self.keyRelease
                        ) as listener: 

            listener.join()
    

