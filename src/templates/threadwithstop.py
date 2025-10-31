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

from threading import Thread, Event
from functools import partial


class ThreadWithStop(Thread):
    def __init__(self, pause=0.001, *args, **kwargs):
        """An extended version of the thread superclass, it contains a new attribute (_event) and a new method (stop).
        The '_event' flag can be used to control the state of the 'run' method and the 'stop' method can stop the running by changing its value.

        Parameters
        ----------
        pause : float, optional
            The pause duration in seconds between thread work cycles (default is 0.01)

        Raises
        ------
        ValueError
            the 'target' parameter of the constructor have to be a unbounded function

        Examples
        --------
        Creating a new subclass of 'ThreadWithStop' superclass:

            class AThread(ThreadWithStop):
                def thread_work(self):
                    ...

            th1 = AThread(pause=0.05)  # Custom pause of 50ms
            th1.start()
            ...
            th1.stop()
            th1.join()


        An example with local function and without subclass definition:

            def examplesFunc(self,param):
                ...

            th1 = ThreadWithStop(target = examplesFunc, args = (param,), pause=0.1)
            th1.start()
            ...
            th1.stop()
            th1.join()

        """

        # Check the target parameter definition. If it isn't a bounded method, then we have to give like the first parameter the new object. Thus the run method can access the object's field, (like self._running).
        if "target" in kwargs:
            if not hasattr(kwargs["target"], "__self__"):
                kwargs["target"] = partial(kwargs["target"], self)
            else:
                raise ValueError("target parameter must be a unbounded function")

        super(ThreadWithStop, self).__init__(*args, **kwargs)
        self._blocker = Event()
        self._pause_event = Event()
        self._pause_event.set()  # start in running state
        self._pause = pause 

    def run(self):
        while not self._blocker.is_set():
            # wait for pause event
            self._pause_event.wait()
            
            # check again if we should stop
            if self._blocker.is_set():
                break
                
            # handle the state change
            self.state_change_handler()
            
            # do the actual work
            self.thread_work()
            
            # respect the pause duration if not paused
            if self._pause_event.is_set():
                self._blocker.wait(self._pause)

    def thread_work(self):
        """This method is called to do the actual work of the thread. It will be overridden by the child thread."""
        pass

    def state_change_handler(self):
        """This method is called to handle the state change of the thread. It will be overridden by the child thread."""
        pass

    def pause(self):
        """Pause the thread execution. The thread will stop processing but remain alive."""
        self._pause_event.clear()

    def resume(self):
        """Resume the thread execution if it was paused."""
        self._pause_event.set()

    def is_paused(self):
        """Check if the thread is currently paused."""
        return not self._pause_event.is_set()

    def stop(self):
        """This method has role to stop the thread by setting the '_event' flag to false value."""
        # resume first in case it's paused so it can process the stop signal
        if self.is_paused():
            self.resume()
        self._blocker.set()
