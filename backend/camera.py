import cv2
from imutils.video import VideoStream
import time

# Try importing Picamera2 safely
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False

class Camera:
    def __init__(self, use_picamera=True):
        self.use_picamera = use_picamera
        self.stream = None

        # Handle unavailable Picamera gracefully
        if self.use_picamera and not PICAMERA_AVAILABLE:
            raise RuntimeError("Picamera2 is not available but required by configuration.")


    def start(self):
        if self.stream is None:
            if self.use_picamera and PICAMERA_AVAILABLE:
                print("Starting Picamera2...")
                self.stream = Picamera2()
                self.stream.start()
            else:
                print("Starting VideoStream...")
                self.stream = VideoStream(src=0).start()
                time.sleep(2.0)  # Warm-up time for webcam

    def get_frame(self):
        if self.use_picamera and PICAMERA_AVAILABLE:
            frame_in = self.stream.capture_array()
            frame = cv2.cvtColor(frame_in, cv2.COLOR_RGB2BGR)
        else:
            frame = self.stream.read()

        #_, jpeg = cv2.imencode('.jpg', frame)
        return frame #jpeg.tobytes()

    def stop(self):
        if self.stream:
            self.stream.stop()