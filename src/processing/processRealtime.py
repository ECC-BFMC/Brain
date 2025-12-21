from src.templates.workerprocess import WorkerProcess
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.utils.messages.allMessages import mainCamera, Signal, SpeedMotor, WarningSignal
from src.templates.threadwithstop import ThreadWithStop
import base64, numpy as np, cv2, time

class threadRealtime(ThreadWithStop):
    def __init__(self, queueList, logger, debugger):
        super().__init__(pause=0.01)
        self.sub = messageHandlerSubscriber(queueList, mainCamera, "lastOnly", True)
        self.event_sender = messageHandlerSender(queueList, Signal)
        self.speed_sender = messageHandlerSender(queueList, SpeedMotor)
        self.warn_sender = messageHandlerSender(queueList, WarningSignal)
        self.logger = logger
        self.debugger = debugger

    def thread_work(self):
        msg = self.sub.receive()
        if msg is None:
            return
        try:
            data = base64.b64decode(msg)
            arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            # --- real-time processing here ---

            mean_brightness = float(frame.mean())
            try:
                self.logger.info("Realtime brightness: %.2f", mean_brightness)
            except Exception:
                print("Realtime brightness: ", mean_brightness)

            # send simple signal if very bright
            if mean_brightness > 200:
                try:
                    self.event_sender.send(f"bright:{mean_brightness:.2f}")
                except Exception:
                    pass

            # Simple obstacle detection using center-crop edge density
            self.detect_obstacle(frame)

            # --- end of processing ---
        except Exception as e:
            if self.debugger:
                self.logger.error("Realtime decode error: %s", e)

    def detect_obstacle(self, frame):
        try:
            h, w = frame.shape[:2]
            cx1 = int(w * 0.3)
            cy1 = int(h * 0.3)
            cx2 = int(w * 0.7)
            cy2 = int(h * 0.7)
            crop = frame[cy1:cy2, cx1:cx2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = edges.mean() / 255.0
            self.logger.debug("Realtime edge_density: %.4f", edge_density)

            if edge_density > 0.06:
                now = time.time()
                if not hasattr(self, "_last_stop_time") or (now - self._last_stop_time) > 1.0:
                    self._last_stop_time = now
                    try:
                        self.speed_sender.send("0")
                    except Exception:
                        pass
                    try:
                        self.warn_sender.send(f"obstacle:{edge_density:.4f}")
                    except Exception:
                        pass
        except Exception as e:
            if self.debugger:
                self.logger.error("Obstacle detection error: %s", e)

class processRealtime(WorkerProcess):
    def __init__(self, queueList, logging, ready_event=None, debugging=False):
        self.queuesList = queueList
        self.logging = logging
        self.debugging = debugging
        super(processRealtime, self).__init__(self.queuesList, ready_event)

    def _init_threads(self):
        self.threads.append(threadRealtime(self.queuesList, self.logging, self.debugging))