GpsTracker 
===============


GpsTracker module is designed to communicate a indoor localization system, provided by the 
organizers. It requires that you are connected to the same local wifi network both with the robot and with the server 
and to place an Aruco marker (given by the organizers) on the car roof, where our localization system easily can detect it. 
The id of the marker will be the same as the one that you will use for the connection to the gps. 
The server streams it's ip on the network, the client then creates a connection with it, where it listens the coordinates afterwards. 
In the subscription state, 
the client have to transmit the id number of robot and it receives a message and a signature. Based on that 
the client can authenticate the server. In this phase create the connection (socket) with the server, which will 
keep alive until robot terminates the run on the race track. 

.. automodule:: src.data.gpstracker.gpstracker
.. automodule:: src.data.gpstracker.server_data
.. automodule:: src.data.gpstracker.server_listener
.. automodule:: src.data.gpstracker.server_subscriber
.. automodule:: src.data.gpstracker.position_listener

Testing
########

If you incorporate the below described module in your application and you want to test it, then this application 
helps to verify the working with the localization system. You have to enter in the folder 'test\gpstrackerSERVER',
where you have run the gps.py module. This module will run a server on your remote device and this server will send 
unreal coordinates for your gpstracker on the robot. The server writes on screen the states of process, you can 
follow functionality. The given server is only a part of it and it works with unreal coordinates. If you want to introduce other 
coordinates based on your robot movements, you need to modify only 'GenerateData' class.