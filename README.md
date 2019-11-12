# BFMC - Start-up ptoject

This repository represents a tool which shows and allows you to start-up your car easier. In this project the following functionalities are implemented in Python:
  - a simple multithread/multiprocess architecture 
  - utility tools/packages for a better development experience
   
  
## General architecture
![architecture](docs/source/diagrams/pics/generalArchitecture.png)
The above image illustrates the general overview of a possible architecture. It is a layered architecture where each node (colored rectangle) represents a process. The gray rectangles denotes the modules/packages, which are not implemented. The inter-process communication is done with pipes. The main ideas, that we followed in the development of this architecture, were modularity and the ease of modification anywhere and anytime. A range of tools have been created for development and debugging. 

### The application structure:

Hardware Layer:
  * Camera Handler
  * Serial Handler

Data Acquisition Layer:
  * Lane Detector
  * Object Detector
  * Sensor Processor
  * GPS Tracker 

Brain Layer:
  * Data Fusion
  * Decision Making
        

### Development and debugging tools:
  * Camera Spoofer
  * Remote Control
  * Camera Streamer

To see the full documentation for each component, please follow the links above [to be completed].

## Installation 

The applications was tested with Python3.7, but there are compatible with other version of Python3. For using the implemented applications you have to install the Python API of Opencv (`cv2`) on the remote device and your Raspberry. If you are using Debian based operating system, you can do it easily by running the following code in terminal:

```
  sudo apt-get install python3-opencv
```

The `requirements` files contains the other dependencies, they are different for the Raspberry Pi and your remote device. The script, which runs on Raspberry Pi, depends on `pySerial`, `picamera`, `cv2` code libraries. The remote debug and development tools relies on `pynput` and `cv2` libraries. You can install these libraries by applying the following codes:
  
**Raspberry Pi**
```
  pip3 install -r requirements_rpi.txt
```

**PC**
```
  pip3 install -r requirements_remote.txt
```

**Note:**
  The remote tools were tested on Linux and Windows. On Linux they are worked correctly without any error. On Windows the camera receiver works nicely, but 
the remote controller transmitter may produce a delay. On Mac Os the remote tools weren't tested. 

## Configuration

The first step before being able to test the platform and add more functionalities to it is to configure the scripts that one can find in this repository. To do so, you will have to set of your IP addresses, for your Raspberry and for your PC, and, if necessary, the ports used for communication. This configuration should occur every time the IP of one of your devices has changed.

The following files should be considered:
    
  ```
  src/utils/camerastreamer/camerastreamer.py
  src/utils/camerastreamer/camerareceiver.py
  
  src/utils/remotecontrol/remotecontroltransmitter.py
  src/utils/remotecontrol/remotecontrolreceiver.py

  ```
Note: You have to change the IP parameters only in `RemoteControlTransmitter` and `CameraStreamer` classes, where they are class member parameters, named `serverIp`.

## How to control your car

In order to control your car, you will have to start your application onto RaspberryPi and enable from `main.py` the Remote Control feature, by setting the `enableRc` flag to true value. Also, you will have to launch the Remote Control Transmitter on your PC and make sure that the IP of your devices are configured correctly. 
After that, run the following:

**Raspberry Pi**
```
python3 main.py
```

**PC**
```
python3 -m bin.remotecontroltransmitter
```


## How to stream your camera
If you want to stream the camera and view on the remote device, you will have to start the same application onto RaspberryPi and enable from `main.py` the Camera Steamer feature, by changing the `enableStream` flag to true value. On the remote device you will have to run the Camera Receiver script. The IP address of the remote device must be introduced in the `CameraStreamer` class. After the configuration, you can run the following code: 

**Raspberry Pi**
```
python3 main.py
```

**PC**
```
python3 -m bin.camerareceiver
```
