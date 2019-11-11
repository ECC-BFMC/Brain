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
from threading import Thread
from functools import partial
from inspect import signature

class ThreadWithStop(Thread):
    def __init__(self,*args,**kwargs):
        """An extended version of the thread superclass, it contains a new attribute (_running) and a new method (stop).
        The '_running' flag can be used to control the state of the 'run' method and the 'stop' method can stop the running by changing its value.
        
        Raises
        ------
        ValueError
            the 'target' parameter of the constructor have to be a unbounded function

        Examples
        --------
        Creating a new subclass of 'ThreadWithStop' superclass:

            class AThread(ThreadWithStop):
                def run(self):
                    while sel._running:
                        ...
            
            th1 = AThread()
            th1.start()
            ...
            th1.stop()
            th1.join()
        
        
        An example with local function and witouth subclass definition:

            def examplesFunc(self,param):
                while self._running
                    ...
            
            th1 = ThreadWithStop(target = examplesFunc, args = (param,))
            th1.start()
            ...
            th1.stop()
            th1.join()

        """

        #Check the target parameter definition. If it isn't a bounded method, then we have to give like the first parameter the new object. Thus the run method can access the object's field, (like self._running).
        if 'target' in kwargs:
            if not hasattr(kwargs['target'], '__self__'):
                kwargs['target'] = partial(kwargs['target'],self)
            else:
                raise ValueError("target parameter must be a unbounded function")
        super(ThreadWithStop,self).__init__(*args,**kwargs)
        self._running = True

    def stop(self):
        """This method has role to stop the thread by setting the '_running' flag to false value. 
        """
        self._running = False
    

