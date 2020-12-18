ObstacleHandler 
===============


ObstacleHandler module is designed to communicate to the environmental server, provided by the 
organizers. It requests to connect the local wifi network with the robot. The ObstacleHandler discovers automatically
the server and create a connection with it, it then streams the coordinates of the position of ostacle as an event/request. 
In the subscription state, the client have to transmit the id number of robot and it receives a message and a signature. Based on them 
the client can authenticate the server. In this phase create the connection (socket) with the server, which will 
keep alive until the script is stopped . 

.. automodule:: src.data.ObstacleHandler.obstacle_handler
.. automodule:: src.data.ObstacleHandler.server_data
.. automodule:: src.data.ObstacleHandler.server_listener
.. automodule:: src.data.ObstacleHandler.server_subscriber
.. automodule:: src.data.ObstacleHandler.obstacle_streamer

Testing
########

If you incorporate the below described module in your application and you want to test it, then this application 
helps to verify the working with the environmental server You have to enter in the folder 'test\obstaclehandlerSERVER',
where you have run the env.py module. This module will run a server on your remote device and this server will "send" 
unreal coordinates and unreal detected obstacles. The server writes on screen the car id, the obstacle and it's coordonate, 
so that you can follow the functionality. If you want to introduce other coordinates and obstacles based on your robot 
movements, you need to just access the send method from obstaclehandler object