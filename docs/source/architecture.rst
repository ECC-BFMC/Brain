Architecture of the tools
=========================

In this section is presented the architecture of the development tools, Camera Streamer and Remote Control. In the fist figure 
is shown the structure of our application, where the remote controller and the camera streamer features are activated and connected to a remote device. 
On the RaspberryPi (RcCar) following processes run: CameraProcess, SerialHandler, CameraStreamer and RemoteControlReceiver, where the first two process 
take part of the hardware layer and the second two are implemented in the `utils` package. Each process contains minimum one thread, these threads are 
symbolized by rectangles and the communication (multiprocess.Pipe and socket.socket) between them by arrows. 

.. image:: diagrams/pics/ComponentDia_StartUp.png
    :align: center

On the remote device run the camera receiver and the remote control transmitter processes, where the Remote control transmitter process contains only two thread, SendCommand and KeyboardListener. 
The third shown object just implements a state machine for the keyboard controller, it is not the independent thread. It generates the message based on keyboard event by applying `getMessage` method.


On the second image a simple structure is presented, which shows mode of usage for steaming the recorded videos by 'CameraSpoofer' process. 
In this case the `enableStream` and `enableCameraSpoof` flags have to enable, where the `CameraProcess` will be in replaced by 'CameraSpoofer' process. 
It will work similarly like the `CameraProcess`, only will play the stored videos.

.. image:: diagrams/pics/ComponentDia_CameraSpoofer.png
    :align: center



