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
    

