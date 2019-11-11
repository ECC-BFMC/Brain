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
import multiprocessing
from multiprocessing import Process, Event

class WorkerProcess(Process):

    def __init__(self, inPs, outPs, daemon = True):
        """WorkerProcess is an abstract class for description a general structure and interface a process.
        
        Parameters
        ----------
        inPs : list(Pipe)
            input pipes 
        outPs : list(Pipe)
            output pipes 
        daemon : bool, optional
            daemon process flag, by default True
        """
        super(WorkerProcess,self).__init__()

        self.inPs = inPs
        self.outPs = outPs

        self.daemon = daemon
        self.threads = list()

        self._blocker = Event()

    
    def _init_threads(self):
        """ It initializes the threads of the process and adds the thread to the 'threads' list, which will be automatically started and stopped in the 'run' method.

        Raises
        ------
        NotImplementedError
            Have to implement the initialization of threads
        """
        raise NotImplementedError

    def run(self):
        """This method applies the initialization of the theards and starts all of them. The process ignores the keyboardInterruption signal and can terminate by applying the 'stop' method. 
        The process will be blocked, until an other process use the 'stop' function. After appling the function it terminates all subthread.
        """
        self._init_threads()
        for th in self.threads:
            th.daemon = self.daemon
            th.start()
        
        # Wait to set internal flag true for the event
        while not self._blocker.is_set():
            try:
                self._blocker.wait()
            except KeyboardInterrupt: # Ignoring the KeyboardInterrupt signal.
                pass
        
        for th in self.threads:
            if hasattr(th,'stop') and callable(getattr(th,'stop')):
                th.stop()
                th.join(0.1)
                if th.is_alive():
                    print("The thread %s cannot normally stop, it's blocked somewhere!"%(th))
                    del th
            else:
                del th
    
    def stop(self):
        """This method stops the process by set the event, which has role to block the running of process, while the subthread executes their functionalities. 
        The main process or other process throught this method can stop the running of this process.
        """
        self._blocker.set()
        