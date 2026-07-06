# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

import cv2
import os
from datetime import datetime
try:
    import picamera2
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False
import time
from threading import Lock

from src.hardware.camera.mock.offlineCamera import OfflineCamera
from src.utils.messages.allMessages import (
    mainCamera,
    serialCamera,
    Recording,
    Record,
    Brightness,
    Contrast,
    StateChange,
)
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.templates.threadwithstop import ThreadWithStop
from src.statemachine.systemMode import SystemMode
from src.utils.logConfig import get_logger
from src.utils.sharedFrameBuffer import (
    SharedFrameWriter,
    CAMERA_SHM_NAME,
    CAMERA_MAIN_SHM_NAME,
)

class threadCamera(ThreadWithStop):
    """Thread which will handle camera functionalities.\n
    Args:
        queuesList (dictionar of multiprocessing.queues.Queue): Dictionar of queues where the ID is the type of messages.
        debugger (bool): A flag for debugging.
    """

    # ================================ INIT ===============================================
    def __init__(self, queuesList, debugger, use_mock=False):
        super(threadCamera, self).__init__(pause=0.001)
        self.queuesList = queuesList
        self.logger = get_logger("Camera")
        self.debugger = debugger
        self.use_mock = use_mock
        self.frame_rate = 15  # recording playback fps; frames are written on this cadence
        self.recording = False
        self.video_writer = None
        self.recordingsDir = os.path.join("runtime", "recordings")
        self._nextRecordFrameDue = 0.0
        self._lastHousekeeping = 0.0
        self._streamLock = Lock()

        self.recordingSender = messageHandlerSender(self.queuesList, Recording)
        self.mainCameraSender = messageHandlerSender(self.queuesList, mainCamera)
        self.serialCameraSender = messageHandlerSender(self.queuesList, serialCamera)

        # Demand-driven streams: raw frames go into shared memory plus a small
        # gateway notification ({"seq", "timestamp", "shm", "shape"}), but only
        # while the stream's sender reports hasSubscribers() - so consumers
        # pick a stream just by subscribing to mainCamera/serialCamera.
        self._streams = {
            "mainCamera": {"shm": CAMERA_MAIN_SHM_NAME, "writer": None, "sender": self.mainCameraSender},
            "serialCamera": {"shm": CAMERA_SHM_NAME, "writer": None, "sender": self.serialCameraSender},
        }

        self.subscribe()
        self._init_camera()

    def subscribe(self):
        """Subscribe function. In this function we make all the required subscribe to process gateway"""

        self.recordSubscriber = messageHandlerSubscriber(self.queuesList, Record, "lastOnly", True)
        self.brightnessSubscriber = messageHandlerSubscriber(self.queuesList, Brightness, "lastOnly", True)
        self.contrastSubscriber = messageHandlerSubscriber(self.queuesList, Contrast, "lastOnly", True)
        self.stateChangeSubscriber = messageHandlerSubscriber(self.queuesList, StateChange, "lastOnly", True)

    # ============================ PERIODIC HOUSEKEEPING ==================================
    def _housekeeping(self):
        """Runs on the camera thread at most once per second: publishes the
        recording flag and applies pending brightness/contrast settings.
        (Replaces the old self-rearming threading.Timer callbacks, so nothing
        touches the camera from another thread and nothing fires after stop.)"""
        now = time.monotonic()
        if now - self._lastHousekeeping < 1.0:
            return
        self._lastHousekeeping = now
        if self.recordingSender.hasSubscribers():
            self.recordingSender.send(self.recording)
        self._applyCameraControls()

    def _applyCameraControls(self):
        """Applies pending brightness/contrast messages to the camera."""
        if self.camera is None:
            return
        message = self.brightnessSubscriber.receive()
        if message is not None:
            if self.debugger:
                self.logger.info(str(message))
            self.camera.set_controls(
                {
                    "AeEnable": False,
                    "AwbEnable": False,
                    "Brightness": max(0.0, min(1.0, float(message))), # type: ignore
                }
            )
        message = self.contrastSubscriber.receive()
        if message is not None:
            if self.debugger:
                self.logger.info(str(message))
            self.camera.set_controls(
                {
                    "AeEnable": False,
                    "AwbEnable": False,
                    "Contrast": max(0.0, min(32.0, float(message))), # type: ignore
                }
            )

    # ================================ RUN ================================================
    def thread_work(self):
        """This function will run while the running flag is True.
        It captures frames from the camera and publishes each demanded stream:
        raw pixels into shared memory, a small notification through the gateway."""
        self._housekeeping()

        # If no real camera exists in dev mode, publish pre-built offline frames at 1 fps.
        if self.camera is None:
            if hasattr(self, "offlineCamera"):
                main_frame, serial_frame = self.offlineCamera.next_frame()
                if self.mainCameraSender.hasSubscribers():
                    self._publishStream("mainCamera", main_frame)
                if self.serialCameraSender.hasSubscribers():
                    self._publishStream("serialCamera", serial_frame)
            time.sleep(1)
            return

        try:
            recordRecv = self.recordSubscriber.receive()
            if recordRecv is not None:
                self._handleRecordToggle(bool(recordRecv))
        except Exception:
            self.logger.exception("Failed to handle the record toggle")

        try:
            wantsMainStream = self.mainCameraSender.hasSubscribers()
            wantsSerial = self.serialCameraSender.hasSubscribers()
            wantsMain = self.recording or wantsMainStream
            if not wantsMain and not wantsSerial:
                time.sleep(0.1)  # nobody is listening: idle instead of spinning
                return

            if wantsMain:
                mainRequest = self.camera.capture_array("main")
                if self.recording:
                    self._recordFrame(mainRequest)
                if wantsMainStream:
                    self._publishStream("mainCamera", mainRequest)

            if wantsSerial:
                serialRequest = self.camera.capture_array("lores")  # Will capture an array that can be used by OpenCV library
                serialRequest = cv2.cvtColor(serialRequest, cv2.COLOR_YUV2BGR_I420) # type: ignore
                self._publishStream("serialCamera", serialRequest)
        except Exception:
            self.logger.exception("Camera capture failed")

    # ============================ STREAM PUBLISHING ======================================
    def _publishStream(self, name, frame):
        """Writes the raw frame into the stream's shared memory segment and
        notifies subscribers through the gateway."""
        if self._blocker.is_set():
            return

        stream = self._streams[name]
        try:
            with self._streamLock:
                if self._blocker.is_set():
                    return
                if stream["writer"] is None:
                    # created on first demand, sized from the actual frame
                    stream["writer"] = SharedFrameWriter(name=stream["shm"], shape=frame.shape, history=1)
                timestamp = time.time()
                seq = stream["writer"].write(frame, timestamp)
                stream["sender"].send(
                    {
                        "seq": seq,
                        "timestamp": timestamp,
                        "shm": stream["shm"],
                        "shape": list(frame.shape),
                    }
                )
        except Exception:
            self.logger.exception(f"Failed to publish the {name} stream")

    # =============================== RECORDING ===========================================
    def _handleRecordToggle(self, enable):
        """Starts or stops recording; repeated same-state toggles are ignored."""
        if enable and not self.recording:
            self._nextRecordFrameDue = time.monotonic()
        elif not enable and self.recording:
            self._stopRecording()
        self.recording = enable

    def _recordFrame(self, frame):
        """Writes frames on a fixed time cadence (frame_rate) so playback speed
        matches real time regardless of how fast the capture loop runs."""
        now = time.monotonic()
        if now < self._nextRecordFrameDue:
            return

        if self.video_writer is None:
            # created lazily so the size always matches what the camera delivers
            os.makedirs(self.recordingsDir, exist_ok=True)
            path = os.path.join(
                self.recordingsDir,
                datetime.now().strftime("recording_%Y-%m-%d_%H-%M-%S.avi"),
            )
            fourcc = cv2.VideoWriter_fourcc(*"XVID") # type: ignore
            height, width = frame.shape[:2]
            self.video_writer = cv2.VideoWriter(path, fourcc, self.frame_rate, (width, height))
            self.logger.info(f"Recording to {path}")

        self.video_writer.write(frame)
        self._nextRecordFrameDue += 1.0 / self.frame_rate
        if self._nextRecordFrameDue < now:
            self._nextRecordFrameDue = now  # fell behind: skip ahead instead of bursting

    def _stopRecording(self):
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

    # ================================ STATE CHANGE HANDLER ========================================
    def state_change_handler(self):
        message = self.stateChangeSubscriber.receive()
        if message is not None:
            modeDict = SystemMode[message].value["camera"]["thread"]

            if "resolution" in modeDict:
                get_logger("Camera Thread").info(f"Resolution changed to {modeDict['resolution']}")

    # ================================ INIT CAMERA ========================================
    def _init_camera(self):
        """This function will initialize the camera object. It will make this camera object have two chanels "lore" and "main"."""

        if self.use_mock:
            self._init_offline_camera("Mock mode enabled")
            return

        if not HAS_PICAMERA2:
            self.camera = None
            get_logger("Camera Thread").error("No picamera2 available. Camera functionality will be disabled.")
            return

        try:
            # check if camera is available
            if len(picamera2.Picamera2.global_camera_info()) == 0:
                self.camera = None
                get_logger("Camera Thread").error(f"No camera detected. Camera functionality will be disabled.")
                return
            
            self.camera = picamera2.Picamera2()
            config = self.camera.create_preview_configuration(
                buffer_count=1,
                queue=False,
                main={"format": "RGB888", "size": (2048, 1080)},
                lores={"size": (512, 270)},
                encode="lores",
            )
            self.camera.configure(config) # type: ignore
            self.camera.start()
            get_logger("Camera Thread").info(f"Camera initialized successfully")
        except Exception as e:
            self.camera = None
            get_logger("Camera Thread").error(f"Failed to initialize camera: {e}")

    def _init_offline_camera(self, reason):
        self.offlineCamera = OfflineCamera()
        self.camera = None
        get_logger("Camera Thread").info(f"{reason}. Using OFFLINE placeholder sequence.")

    # =============================== STOP ================================================
    def stop(self):
        super(threadCamera, self).stop()
        self.recording = False
        self._stopRecording()
        if self.camera is not None:
            self.camera.stop()
        with self._streamLock:
            for stream in self._streams.values():
                if stream["writer"] is not None:
                    stream["writer"].close()
                    stream["writer"] = None
