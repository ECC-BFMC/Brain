Camera Handler
===============


In this section, you can find the documentation of the camera handler, which is built from a camera process and a camera publisher. 
The camera process is a base processes, which contains the publisher thread. The publisher sets the camera parameter and capture the frame to transfer other workers (thread or processes) via pipes.
It can handle multiple connection, so can send the frame to multiple workers.

.. automodule:: src.hardware.Camera.CameraProcess
.. automodule:: src.hardware.Camera.CameraPublisher


