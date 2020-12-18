CarsTracker 
===============

CarsTracker module is designed to communicate the indoor positioning and orientation of the moving obstacle/car, run by the Organizers. 
It listenes to the 50009 port, where every moving car streams it's own information (ID, Position and Orientatio). This tread is used in order 
to simulate the bluetooth communication between smart cars in a smart city (connectivity field). The information can be used in order to validate 
the position of the cars so to avoid eventual collision. 

.. automodule:: src.data.carstracker.carstracker

Testing
########

If you incorporate the below described module in your application and you want to test it, then this application 
helps to verify the working with the tracking system. You have to enter in the folder 'test\carstrackerSIM',
where you have run the broadcaster.py module. This module will run a simulated car on your remote device and it will send 
unreal coordinates for your carstracker module on the robot. The server writes on screen the states of process, you can 
follow functionality. It is a thread, so it can be run in parallel, and you can access the informations with ID, pos and rot attributes of the method.