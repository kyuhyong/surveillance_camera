import cv2
from flask import Flask, Response

app = Flask(__name__)

#camera = cv2.VideoCapture(0,cv2.CAP_V4L2)

def generate_video_stream():
    """Generate frames for live video streaming"""
    camera = cv2.VideoCapture(0)
    while True:
        #camera = cv2.VideoCapture(0)
        success, frame = camera.read()
        if not success:
            continue  # Skip the frame if it fails to read

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/api/video_stream')
def video_stream():
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
