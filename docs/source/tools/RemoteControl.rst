Remote Control
==============

The next section describes all component for a remote controller. 
The RemoteControlTransmitter class has purpose to transmit all command received from other process to RemoteControlReceiver. The RemoteControlReceiver sends forward the command to other processes.
These two classes create the connection based on UPD protocol between two device, like your laptop and the robot. The KeyboardListener is a thread for capturing and filtering the keyboard events.
The RcBrain class is the main control mechanism, which based on the keyboard events calculates the robot state, like forward speed and steering angle. It's responsible for processing the keyboard 
events and setting a parameters for control commands.

.. image:: ../diagrams/pics/ClassDiaStartUp_RemoteControl.png
    :align: center

.. automodule:: src.utils.remotecontrol.remotecontroltransmitter
.. automodule:: src.utils.remotecontrol.remotecontrolreceiver
.. automodule:: src.utils.remotecontrol.keyboardlistener
.. automodule:: src.utils.remotecontrol.rcbrain

