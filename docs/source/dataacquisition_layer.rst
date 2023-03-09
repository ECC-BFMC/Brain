Data acquisition layer
=======================

The data acquisition layer contains all the API's necessary in order to communicate with all the systems present at the location.
For every API, a simulated system was designed, which you can run on a different machine and create a real connection, identical 
with the one you will find here, and communicate unreal information. This will help you ensure the integrity of the packages and 
of the functionalities. 

For every API, the testing module is also described in the links below.

All the simulated components given by the organizers have to be run with python2.7!

The given client API's are python2.7 and python3.7 compatible

Both the car and the remote machine/s have to be on the same network.

V2V - Vehicle to vehicle communication 
----------------------------------------

vehicletovehicle is a module designed to get the indoor positioning and orientation of the moving obstacle/car, run by the Organizers. 
The moving vehicles stream their position on the network on the 5009 port, by using the UDP protocoal. This API starts a Thread that gets
all the data and saves it as it's attributes (ID, position and angle). 

This simulates the bluetooth communication between smart cars in a smart city (connectivity field).

The information can be used in order to double validate the position of the cars so to avoid eventual collision. 

Traffic Lights
---------------

trafficlights is a module designed to get the ID and the state of the traffic lights on the map. 
The traffic lights stream their position on the network on the 5007 port, by using the UDP protocoal. This API starts a Thread that gets
all the data and saves it as it's attributes (ID and states). 

This simulates the bluetooth communication between smart cars and the infrastructure in a smart city (connectivity field). 

The information can be used in order to double validate the state of a traffic light so to avoid eventual collision. 

Localisation system
--------------------

localisationsystem is a module designed to get the position and orientation of the car itself on the map from the Localisation System server. 
The server streams it's TCP port on the broadcast port (12345). The client then tries to connect to the server on the communicated TCP port, by sending it's
own ID. The server replies with a plain and an encrypted message with it's own private key. The client decrypts the encrypted message with the server public
key and checks that the messages are the same. If the messages are the same, the server is validated by the client and the connection is initiated. 
The server then serves the client with it's position and orientation on the map. 

This simulates the real life GPS. 

The information can be used in order to validate the position on the track at each moment, making the car independent to a starting point. 

More details on the connection itself can be found in the src/data/localisationsystem/server_subscriber.py

Live traffic system
--------------------

livetraffic is a module designed so that the clients/cars can send the coordinates of obstacles to the server, which, this way, can monitor 
the traffic conditions on the track.
The server streams it's TCP port on the broadcast port (23456). The client then tries to connect to the server on the communicated TCP port, by sending it's
own ID and the ID crypted with the car PrivateKey. The server decrypts the car encrypted message with corresponding public key. If the ID's match, that means
that the client is valdiated by the server. The server then replies with a plain and an encrypted message with it's own private key. The client decrypts the 
encrypted message with the server public key and checks that the messages are the same. If the messages are the same, the server is validated by the client 
and the connection is initiated. The server then serves the client by listening to the ID's and obstacles it will send. 

This simulates a real life automatic traffic monitor, which updates itself by using the data from the connected devices.

More details on the connection itself can be found in the src/data/environmentalserver/server_subscriber.py

The information can be used by the team as a validation that the car is detecting the obstacles.
