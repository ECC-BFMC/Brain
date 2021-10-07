Utils layer
===========

Camera Steamer
-----------------------

Camera streamer and camera receiver classes can be used for transferring the frames captured by the camera to a remote device. 
The CameraStreamerProcess connects to the CameraProcess through the first input pipe and transfers the frames to the CameraReceiverProcess, on the remote client.
The receiver connects to the RcCar and shows the frames received from the streamer.  

.. image:: diagrams/pics/ClassDiaStartUp_CameraStreamer.png
    :align: center

.. automodule:: src.utils.camerastreamer.CameraStreamerProcess
.. automodule:: src.utils.camerastreamer.CameraReceiverProcess


Remote Control
-------------------------

The next section describes all component for a remote controller. 
The RemoteControlTransmitterProcess class has the purpose to transmit all command received from the RcBrainThread & KeyboardListenerThread  
to RemoteControlReceiverProcess. The RemoteControlReceiver forward the command to the SerialHandlerProcess. The process handle the transmisson 
and receiving of the ok message to & from the Nucleo board. 

.. image:: diagrams/pics/ClassDiaStartUp_RemoteControl.png
    :align: center

.. automodule:: src.utils.remotecontrol.RemoteControlTransmitterProcess
.. automodule:: src.utils.remotecontrol.RemoteControlReceiverProcess
.. automodule:: src.utils.remotecontrol.KeyboardListenerThread
.. automodule:: src.utils.remotecontrol.RcBrainThread
