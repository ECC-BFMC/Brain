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
If you run 

## Cars tracker
If you run 

## Traffic lights interaction
If you run 

## GPS interaction
If you run 

## Obstacle handler
If you run 

[Documentation](https://bfmcstartup.readthedocs.io/en/stable/)