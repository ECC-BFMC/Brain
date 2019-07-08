# BFMC - Start-up ptoject

This repository represents a tool which shows and allows you to start-up your car easier. In this project the following functionalities are implemented:
  - a simple multithread/multiprocess architecture 
  - utility tools/packages for a better development experience
  
  
# Architecture overview
![architecture](https://github.com/NandorKilyenBosch/BFMC.Startup.Priv/blob/master/assets/docs/images/generalArchitecture.png)
The above image illustrates the general overview of a possible architecture. It is a layered architecture where each node (colored rectangle) represents a process. The rectangles marked gray denotes that the module/package has not been implemented. The interprocess-communication is done with pipes. The main ideas that followed me in the developing of this architecture was modularity and the ease of modification anywhere and anytime. For development and debugging some tools have been created.

The application structure:

    Hardware Layer:
        Camera Handler
        Serial Handler

    Data Aquisition Layer:
        Lane Detector
        Object Detector
        Sensor Processor
        GPS Tracker

    Brain Layer:
        Data Fusion
        Decission Making
        

Development and debugging tools:

    Camera Spoofer
    Remote Control
    Camera Streamer

To see the full documentation for each component, please follow the links above [to be completed].

# Out-of-the-box configuration

The first step before being able to test the platform and add more functonalities to it is to configure the scripts that one can find in this repository. To do so, you will have to set of your IP addresses, for your Raspberry and for your PC, and, if neccesary, the ports used for communication. This configuration should occur every time the IP of one of your devices have changed.

The following files should be considered:
    
  ```
  src/utils/CameraStreamer/CameraStreamer.py
  src/utils/CameraStreamer/CameraReceiver.py
  
  src/utils/RemoteControl/RemoteControlTransmitter.py
  src/utils/RemoteControl/RemoteControlReceiver.py

  ```
  
# How to control your car
Inorder to control your car, you will have to start your application onto RaspberryPi and enable from `main.py` the Remote Controller flag. Also, you will have to launch the Remote Controller Script on your PC and make sure that the
After that, run the following:

**Raspberry Pi**
```
python3 main.py
```

**PC**
```
python src/utils/RemoteControl/RemoteControlTransmitter.py
```


# How to stream your camera
