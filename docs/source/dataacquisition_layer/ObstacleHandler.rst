ObstacleHandler 
===============


ObstacleHandler module is designed to communicate to the environmental server, provided by the 
organizers. It requires that you are connected to the same local wifi network both with the robot and with the server. 
The server streams it's ip on the network, The obstacleHandler then opens a TCP/IP connection with the server and sends it's ID and the cripted id
with it's own private key. The server validates that the client is in it's data system by decripting the message with the public key of the client.
The server sends a plain message and a cripted message with it's own private key to the client, the client decripts the message with the corresponding 
public key in order to validate the server. The client then streams the coordinates of the position of encountered ostacle as an event/request. 

.. automodule:: src.data.obstaclehandler.obstacle_handler
.. automodule:: src.data.obstaclehandler.server_data
.. automodule:: src.data.obstaclehandler.server_listener
.. automodule:: src.data.obstaclehandler.server_subscriber
.. automodule:: src.data.obstaclehandler.obstacle_streamer

Testing
########

If you incorporate the below described module in your application and you want to test it, then this application 
helps to verify the working with the environmental server You have to enter in the folder 'test\obstaclehandlerSERVER',
where you have run the env.py module. This module will run a server on your remote device and this client will send 
unreal coordinates and unreal detected obstacles. The server writes on screen the car id, the obstacle and it's coordonate, 
so that you can follow the functionality. It also saves a copy when you close the server.