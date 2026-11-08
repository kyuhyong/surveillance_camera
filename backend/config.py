# Configuration settings
import os

def _picamera2_available():
    try:
        import picamera2  # noqa: F401
        return True
    except ImportError:
        return False

# Camera source:
# - Pi camera module (ribbon cable) must use Picamera2; OpenCV can't read /dev/video0 (unicam).
# - USB webcam / PC uses OpenCV VideoStream.
# Auto-detected (Picamera2 installed -> Pi camera) so the same code works on the PC
# and the Pi. Override with the environment variable USE_PICAMERA=1 / USE_PICAMERA=0.
_use_picamera_env = os.getenv("USE_PICAMERA")
if _use_picamera_env:
    USE_PICAMERA = _use_picamera_env.strip().lower() in ("1", "true", "yes", "on")
else:
    USE_PICAMERA = _picamera2_available()
TARGET_FPS = 20  # Change this value for slower frame rates
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
DETECTION_DURATION = 5
RETENTION_DAYS = 7
CLIPS_FOLDER = 'recorded_clips'
STREAM_FOLDER = 'stream_clips'
IMAGES_FOLDER = 'recorded_images'