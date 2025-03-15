import cv2
from flask import Flask, Response
from picamera2 import Picamera2
from time import sleep

app = Flask(__name__)

#camera = cv2.VideoCapture(0,cv2.CAP_V4L2)


def generate_video_stream():
    """Generate frames for live video streaming"""
    #camera = cv2.VideoCapture(0)
    # PI CAMERA
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
    picam2.set_controls({"FrameRate": 30})
    # Configure AWB mode
    picam2.set_controls({"AwbMode": "auto"})  # Options: "auto", "incandescent", "tungsten", etc.

    camera_config = picam2.create_preview_configuration()
    picam2.configure(camera_config)
    sleep(1)
    picam2.start()
    try:
        while True:
            #camera = cv2.VideoCapture(0)
            # success, frame = camera.read()
            # if not success:
            #     continue  # Skip the frame if it fails to read
            frame = picam2.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', frame_bgr)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    except KeyboardInterrupt:
        print("Exiting...")

    finally:
        camera.stop()
        cv2.destroyAllWindows()    

@app.route('/')
def video_stream():
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
