Traffic Lights
===============

The listener module is designed to receive the messages broadcasted by the semaphores on the track. The device running the code has to be connected to the same LAN as the semaphores. 
This module receives the messages and interprets them, extracting the ID (1, 2, 3) of the source semaphore and its state (0 - RED, 1 - YELLOW, 2 - GREEN), and updates the corresponding members.
Depending on the semaphores' states, the autnomous car can decide on the type of action it has to perform (e.g. enter the trach, enter / not enter an intersection, ...). 

.. automodule:: src.data.trafficlights.Listener

Testing
````````
If you incorporate the listener module into your application and you want to test it, then you have to use a simulator for the semaphores. 
Running the Simulator.py script (in test/trafficlightSIM) starts the simulated semaphores and keeps them running for 60 seconds. These operate as specified by a pattern defined in this file. 
The simulator can be started on the same machine where the listener module runs.

.. automodule:: test.trafficlight.Simulator
