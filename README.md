# BFMC - Start-up ptoject

This repository represents a tool which shows you how to start-up your car easier and use some of the already developed functionalities of the car. In this project the following functionalities are implemented by using Python3.7:
  - a simple multithread/multiprocess architecture 
  - utility tools/packages for a better development experience
  - hardware tools/packages for an communication/interaction with the outside environment
  - a data tool/packages to communicate and access information from the interactive environment
  - a series of simulated elements

.. image:: diagrams/pics/generalArchitecture.png
    :align: center

*Installation* 

The application is compatible with other version of Python3. For using the implemented applications you have to install the Python API of Opencv (`cv2`) on the remote device and your Raspberry. If you are using Debian based operating system, you can do it easily by running the following code in terminal:

```
  sudo apt-get install python3-opencv
```

The `requirements` files contains the other dependencies, they are different for the Raspberry Pi and your remote device. The script, which runs on Raspberry Pi, depends on `pySerial`, `picamera`, `cv2` code libraries. The remote debug and development tools relies on `pynput` and `cv2` libraries. You can install these libraries by applying the following codes:
  
*Raspberry Pi*
```
  pip3 install -r requirements_rpi.txt
```

*PC*
```
  pip3 install -r requirements_remote.txt
```

*Note:*
  The remote tools were tested on Linux and Windows. On Linux they are worked correctly without any error. On Windows the camera receiver works nicely, but the remote controller transmitter may produce a delay. On Mac Os the remote tools weren't tested. 

## Remote car control

*Configurations*

The first step before being able to test the platform and add more functionalities to it is to configure the scripts that one can find in this repository. To do so, you will have to set of your IP addresses, for your Raspberry and for your PC, and, if necessary, the ports used for communication. This configuration should occur every time the IP of one of your devices has changed.

The following files should be considered:
    
  ```
  src/utils/camerastreamer/camerastreamer.py
  src/utils/camerastreamer/camerareceiver.py
  
  src/utils/remotecontrol/remotecontroltransmitter.py
  src/utils/remotecontrol/remotecontrolreceiver.py

  ```
Note: You have to change the IP parameters only in `RemoteControlTransmitter` and `CameraStreamer` classes, where they are class member parameters, named `serverIp`.

*How to control your car*

In order to control your car, you will have to start your application onto RaspberryPi and enable from `main.py` the Remote Control feature, by setting the `enableRc` flag to true value. Also, you will have to launch the Remote Control Transmitter on your PC and make sure that the IP of your devices are configured correctly. 
After that, run the following:

*Raspberry Pi*
```
python3 main.py
```

*PC*
```
python3 -m bin.remotecontroltransmitter
```


*How to stream your camera*
If you want to stream the camera and view on the remote device, you will have to start the same application onto RaspberryPi and enable from `main.py` the Camera Steamer feature, by changing the `enableStream` flag to true value. On the remote device you will have to run the Camera Receiver script. The IP address of the remote device must be introduced in the `CameraStreamer` class. After the configuration, you can run the following code: 

*Raspberry Pi*
```
python3 main.py
```

*PC*
```
python3 -m bin.camerareceiver
```

## BNO displayer

First and foremost, you should check that the wiring between the Raspberry Pi and the IMU board is correct. 

You can check the following pin layout of the IMU board and the pinout of the RPI 4b https://www.raspberrypi.org/documentation/usage/gpio/

.. image:: diagrams/pics/IMULayout.png
    :align: center

For our example, we will use the RTIMULib tool.
In order to install the neccesary tools, the library and enable your I2C communication, please follow this guide: https://github.com/RPi-Distro/RTIMULib/tree/master/Linux

To make the library python compatible, there is one more step to be taken:
```
cd ../python
python3.7 setup.py build
sudo python3.7 setup.py install
```

We have provided two more scripts, BNOhandler.py and BNO_test.py, which should serve as a base for further
development with the sensor. The BNOhandler is a written as a thread and the BNO_test is used as an example of running the thread. They are located under the hardware layer.

For a more thorough understanding of the BNO055's capabilities you should read the official
datasheet at https://www.bosch-sensortec.com/products/smart-sensors/bno055.html and
RTIMULib's documentation on it's official GitHub repository:
https://github.com/RPi-Distro/RTIMULib

### Testing of simulated competition components.

All the simulated components given by the organizers have to be run on python2.7!. 
The given scripts are python2.7 and python3.7 compatible!

## Cars tracker
In order to test the functionality of the cars tracler, we have developed a simulated car streamer, you can find it here: test/carstrackerSIM/broadcaster.py. 
You can run it on a different machine and your listener on your car. It uses the broadcaster.py. The listener (for your car) is located here: src/data/carstracker/carstracker.py. 
It uses the Listener.py as a thread.

## Traffic lights interaction
In order to test the functionality of the traffic lights, we have developed a simulated traffic light, you can check it here: test/trafficlightSIM/Simulator.py. You can run it on a different machine and your listener on your car. The listener is located here: src/data/trafficlights/Example.py. It uses the Listener.py as a thread.

## GPS interaction
In order to test the functionality of the GPS server, we have developed a simulated server, you can find it here: test/gpsstrackerSERVER/gps.py. You can run it on a different machine and your client on your car. The client is lcoated here: src/data/gpstracker/gpstracker.py. It uses all the scripts as threads for connecting, subscribing and position listening.
- For tesing purposes, publickey_server_test.pem should be used (file src/data/gpstracker/server_subscriber.py line 55)
- For the competition, publickey_server.pem should be used (file test/gpstracker/server_subscriber.py line 54)

## Obstacle handler
In order to test the functionality of the obstacle handler server, we have developed a simulated server, you can find it here: test/obstaclehandlerSERVER/env.py. You can run it on a different machine and the client on your own car. The client is located here: src/data/obstaclehandler/obstacle_handler.py. It uses all the scripts as threads for connecting, subscribing and obstacle position streaming.

- The server saves the received data under test/obstaclehandlerSERVER/savings
- For tesing purposes, publickey_server_test.pem should be used (file src/data/obstaclehandler/server_subscriber.py line 57)
- For the competition, publickey_server.pem should be used (file test/obstaclehandler/server_subscriber.py line 56)
- For the competition, a pair of privatekey_client.pem and publickey_client.pem will have to be generated. The publickey_client will have to be sent to the organizers by the communicated channel. If you want to connect with a different id (obstacle_handler.py), the public key corresponding with your private key have to be saved on the test/server/keys with the same id_publickey.pem. The example of id 120 is given.

  // generate a private key with the correct length

  openssl genrsa -out private-key.pem 2048

  // generate corresponding public key

  openssl rsa -in private-key.pem -pubout -out public-key.pem


## Release notes:
- Added two way validation through private&public RSA key pair for obstaclehandlerSERVER. In order to validate the client to the server and the server to the client.
- Added test and competition RSA keys for obstacle handler and gps servers.
- Implemented saving methos of the data for the obstacle handler server, in order to check the sent data.
- Made all the test-ing simulation run on python2.7.
- All the data collectors are runnable both in python2.7 and python3.7.


[Documentation](https://bfmcstartup.readthedocs.io/en/stable/)