Hardware layer
================

Here you can find the element of the hardware layer, which have functionality to create an interface between the hardware component and other part of code.
This layer contains two interface: CameraHandler and SerialHandler. CameraHandler interface controls the camera parameters and captures the frames, 
which transfers to other workers. The serialHanlder communicates with other devices (like a micro-controller) via a serial communication interface and based on predefined message encoding mechanism.

.. toctree::
    :maxdepth: 1

    CameraHandler
    SerialHandler
    
    


