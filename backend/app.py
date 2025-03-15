from flask import Flask, request, jsonify, send_file, Response, session
from flask import send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_session import Session
from flask_socketio import SocketIO, emit
import logging, os, signal, sys, cv2, threading, time, subprocess
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS
from imutils.video import VideoStream
import numpy as np
from camera import Camera
import config

load_dotenv()

app = Flask(__name__, static_folder='build')
socketio = SocketIO(app, cors_allowed_origins="*")

# Suppress Flask's default HTTP request logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # Suppress non-critical logs

# Flask Session Configuration
app.secret_key = 'super-secret-key'  # Required for session security
app.config['SESSION_TYPE'] = 'filesystem'  # Store session data on the server
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session expiry in seconds (e.g., 1 hour)
Session(app)  # Initialize Flask-Session

CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSKEY')
app.default_sender = os.getenv('MAIL_USERNAME')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.secret_key = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)
mail = Mail(app)

# Path to save motion-detected videos
CLIPS_FOLDER = 'recorded_clips'
os.makedirs(CLIPS_FOLDER, exist_ok=True)
STREAM_FOLDER = 'stream_clips'
os.makedirs(STREAM_FOLDER, exist_ok=True)
IMAGES_FOLDER = 'recorded_images'
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Motion detection settings
DETECTION_DURATION = 10   # Recording duration (seconds) after motion is detected
# Desired Frame Rate (FPS)
TARGET_FPS = 25  # Change this value for slower frame rates
FRAME_DELAY = 1.0 / TARGET_FPS  # Delay to match target FPS
# Set retention period in days (e.g., delete files older than 7 days)
RETENTION_DAYS = 7
# Brightness threashold for ready to detect motion
BRIGHTNESS_THREASHOLD = 50

# Motion detection variables
isArmed = False     # Global state to manage ARM/DISARM mode
detection_ready_cnt = 0 # Detection readyness delay
prev_frame = None
last_motion_check = 0
motion_count = 0
brightness = 0
brightness_prev = 0
motion_sensitivity = 3

v_stream = None   # VideoStream
camera = Camera(use_picamera=config.USE_PICAMERA)
is_recording = False
v_writer = None     # Video Writer
recording_timer = None  # To track the timer object
recorded_video_path = ""

sendNotification = False # Notification state

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)

class Clip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
# Lazy Initialization for Video Stream
def get_video_stream():
    global v_stream
    if v_stream is None:
        print("🎥 Initializing video stream...")
        v_stream = VideoStream(src=0).start()
    return v_stream

# Gracefully stop video stream when Flask stops
def release_video_stream():
    global v_stream
    if v_stream is not None:
        print("🔄 Releasing camera...")
        v_stream.stop()
        v_stream = None  # Reset `vs` after releasing the camera
# ============================== #
#         Motion Detection       #
# ============================== #
def check_motion(new_frame):
    global prev_frame
    gray = cv2.cvtColor(new_frame, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    if prev_frame is None:
        prev_frame = gray

    # Compute difference and threshold
    frame_delta = cv2.absdiff(prev_frame, gray)
    _, thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)

    # Dilate the threshold image to fill in holes
    thresh = cv2.dilate(thresh, None, iterations=2)

    # Find contours to detect motion
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detect = 0
    for contour in contours:
        if cv2.contourArea(contour) < 500:  # Ignore small movements
            continue
        detect += 1
    
    prev_frame = gray
    return detect, int(round(np.mean(gray)))
    
def generate_video_stream():
    global is_recording, v_writer, recording_timer, \
        recorded_video_path, last_motion_check, isArmed, \
        motion_count, brightness, motion_sensitivity, detection_ready_cnt
    #vs = get_video_stream() # Initialize vs only when needed
    camera.start()
    while True:
        #frame = vs.read()
        frame = camera.get_frame()
        motion_detected = False

        # Check for motion every 0.5 seconds
        current_time = time.time()
        if current_time - last_motion_check >= 0.5:
            motion_count, brightness = check_motion(frame)
            # Check if image is bright enough to check detection
            if brightness > BRIGHTNESS_THREASHOLD:
                if detection_ready_cnt > 3:
                    if motion_count > motion_sensitivity:
                        motion_detected = True
                else:
                    detection_ready_cnt+=1
            else:
                # Image is too dark for detection so reset count
                detection_ready_cnt = 0
            
            last_motion_check = current_time

        # Get the current time
        current_time = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
        # Define the position and font
        position = (10, 30)  # Position to place the text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        color = (0, 255, 0)  # Green color in BGR
        thickness = 2
        # Overlay the text on the frame
        cv2.putText(frame, current_time, position, font, font_scale, color, thickness)
        
        # Start recording when motion is detected
        if motion_detected and isArmed:
            if not is_recording:
                is_recording = True
                start_recording(frame)

        # Record images to video
        if is_recording and v_writer is not None:
            v_writer.write(frame)

        # Stop recording if switching to DISARMED
        if not isArmed and is_recording:
            stop_recording()

        # Label onscreen message
        txt = ("REC " if is_recording else "" )+"Motion:"+str(motion_count)+" @"+str(detection_ready_cnt)
        cv2.putText(frame, txt, (10, 60), font, font_scale, color, thickness)
        txt = "Brightness:"+str(brightness)
        cv2.putText(frame, txt, (10, 90), font, font_scale, color, thickness)
        
        # Encode frame for live streaming
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        # Reduce frame rate
        time.sleep(FRAME_DELAY)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def save_first_frame(frame, timestamp):
    """Save the first detected frame as an image"""
    image_path = os.path.join(IMAGES_FOLDER, f'image_{timestamp}.jpg')
    cv2.imwrite(image_path, frame)

def start_recording(frame):
    global v_writer, recorded_video_path, recording_timer
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    video_path = os.path.join(CLIPS_FOLDER, f'motion_{timestamp}.mp4')
    print(f"🎥 Motion detected : {video_path}")
    recorded_video_path = video_path
    save_first_frame(frame, timestamp)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    v_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))
    # Start a timer to stop recording after a set duration
    if recording_timer:
        recording_timer.cancel()  # Cancel any active timer
    recording_timer = threading.Timer(DETECTION_DURATION, stop_recording)
    recording_timer.start()

def stop_recording():
    """Stop recording safely with proper resource cleanup"""
    global is_recording, v_writer, recorded_video_path
    if is_recording:
        if v_writer is not None:   # Safely release the VideoWriter
            v_writer.release()
            v_writer = None

        # Convert mp4 video to web-compatible format
        filename = os.path.basename(recorded_video_path)
        converted_path = os.path.join(STREAM_FOLDER, filename)
        convert_to_web_compatible(recorded_video_path, converted_path)
        is_recording = False
        timestamp_str = '_'.join(filename.split('_')[1:3]).replace('.mp4','')
        
        # Format timestamp for display (e.g., "2025-03-11 23:46:30")
        formatted_timestamp = timestamp_str.replace('_', ' ')
        image_filename = filename.replace('.mp4','.jpg').replace('motion','image')

        # Notify frontend with new clip
        socketio.emit('new_clip', {
            "timestamp": formatted_timestamp,
            "image_filename": image_filename, 
            "video_filename": filename
        })
        print(f"🛑 Stopping recording : {datetime.now()}")

# Auto-delete function
def auto_delete_old_clips():
    print(f"AUTO DELETE STARTED!")
    while True:
        now = datetime.now()
        for filename in os.listdir(CLIPS_FOLDER):
            file_path = os.path.join(CLIPS_FOLDER, filename)
            if os.path.isfile(file_path):
                # Extract the date from the filename
                try:                  
                    date_str = '_'.join(filename.split('_')[1:3]).split('.')[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
                    # Calculate file age
                    if (now - file_date).days > RETENTION_DAYS:
                        os.remove(file_path)
                        print(f"🗑️ Deleted old clip: {filename}")
                except (IndexError, ValueError):
                    print(f"❗ Invalid filename format: {filename}")
        
        # Check for old files every 24 hours
        time.sleep(24 * 3600)  # 86400 seconds = 1 day

# Start the auto-delete function in a separate thread
threading.Thread(target=auto_delete_old_clips, daemon=True).start()

@app.route('/api/video_stream')
def video_stream():
    """Live video stream with motion detection"""
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/toggle_mode', methods=['POST'])
def toggle_mode():
    global isArmed
    data = request.json
    isArmed = data.get('isArmed', False)
    status = 'ARMED' if isArmed else 'DISARMED'
    print(f"🔒 Camera mode set to: {status}")
    return jsonify({"message": f"Camera mode is now {status}"})

@app.route('/api/set_notification', methods=['POST'])
def set_notification():
    global sendNotification
    data = request.json
    sendNotification = data.get('sendNotification', False)
    print(f"🔔 Notification setting updated: {sendNotification}")
    return jsonify({"message": f"Notification setting set to {sendNotification}"})

@app.route('/api/set_sensitivity', methods=['POST'])
def set_sensitivity():
    global motion_sensitivity
    data = request.json
    motion_sensitivity = data.get('sensitivity', 3)
    print(f"🎯 Motion detection sensitivity set to: {motion_sensitivity}")
    return jsonify({"message": f"Sensitivity set to {motion_sensitivity}"})

@app.route('/api/clips')
def get_clips():
    """List recorded motion-detected clips"""
    clips = []
    # Collect both video and image data
    for video_file in os.listdir(CLIPS_FOLDER):
        if video_file.endswith('.mp4'):
            timestamp_str = '_'.join(video_file.split('_')[1:3]).replace('.mp4','')
            image_file = f"image_{timestamp_str}.jpg"

            # Format timestamp for display (e.g., "2025-03-11 23:46:30")
            formatted_timestamp = timestamp_str.replace('_', ' ')
            #print(f"video_file = {video_file}")
            #print(f"image_file = {image_file}")
            clips.append({
                "id": len(clips) + 1,
                "video_filename": video_file,
                "image_filename": image_file,
                "timestamp": formatted_timestamp
            })
    return jsonify(clips)

# Serve Images
@app.route('/api/image/<string:filename>')
def view_image(filename):
    try:
        return send_from_directory(IMAGES_FOLDER, filename, mimetype='image/jpeg')
    except FileNotFoundError:
        abort(404, description="Image not found")

# Serve Videos with Streaming Support
@app.route('/api/video/<string:filename>')
def view_video(filename):
    video_path = os.path.join(STREAM_FOLDER, filename)

    if not os.path.exists(video_path):
        abort(404, description="Video file not found")

    print(f"✅ Serving video: {video_path}")
    
    # Correct headers for video playback
    return Response(
        generate_rec_video_stream(video_path),
        mimetype='video/mp4',
        headers={
            'Content-Disposition': f'inline; filename={filename}',  
            'Accept-Ranges': 'bytes'
        }
    )

# Efficient Video Streaming
def generate_rec_video_stream(video_path):
    print(f"🎬 Attempting to stream: {video_path}")
    try:
        with open(video_path, 'rb') as video_file:
            while chunk := video_file.read(1024 * 1024):  # 1MB chunks
                #print(f"📹 Streaming chunk of size: {len(chunk)} bytes")
                yield chunk
    except Exception as e:
        print(f"❌ Error streaming video: {e}")

def convert_to_web_compatible(input_path, output_path):
    """Converts recorded video to web-compatible `.mp4` format"""
    try:
        subprocess.run([
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',
            '-crf', '23',
            '-hide_banner', '-loglevel','error',
            '-preset', 'fast',
            '-movflags', '+faststart',
            output_path
        ], check=True)
        print(f"✅ Conversion successful: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed: {e}")

@app.route('/api/delete_clip/<string:filename>', methods=['DELETE'])
def delete_clip(filename):
    """Delete recorded video"""
    try:
        os.remove(os.path.join(CLIPS_FOLDER, filename))
        os.remove(os.path.join(STREAM_FOLDER, filename))
        image_filename = filename.replace('.mp4','.jpg').replace('motion','image')
        #print(f"DELETE: image_filename={image_filename}")
        os.remove(os.path.join(IMAGES_FOLDER, image_filename))
        return jsonify({"message": "Clip deleted successfully"})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    registration_code = data.get('registration_code')

    # Check if the provided registration code is correct
    if registration_code != app.secret_key:
        return jsonify({"error": "Invalid registration code"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    # Register new user
    new_user = User(username=username, password=password, email=email)
    db.session.add(new_user)
    db.session.commit()

    try:
        msg = Message(
            'Verify Your Accountem Dashbot',
            sender = app.default_sender,
            recipients=[email],
            body=f"Hello {username},\n\nWelcome! Please verify your email by clicking this link: http://localhost:5000/verify/{username}"
        )
        mail.send(msg)
        return jsonify({"message": "Registration successful! Please check your email to verify your account."})
    
    except Exception as e:
        return jsonify({"error": f"Email sending failed: {str(e)}"}), 500
    #return jsonify({"message": "Registration successful! Please verify your email."})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    username = data.get('username')
    if user:
        session['user'] = username # Store user in session
        session.permanent = True  # Ensures persistent session
        return jsonify({"message": "Login successful", "status": "success"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """User Logout Endpoint"""
    session.pop('user', None)
    return jsonify({"message": "Logout successful", "status": "success"})

@app.route('/api/check_session', methods=['GET'])
def check_session():
    """Check if the user is logged in"""
    if 'user' in session:
        return jsonify({"logged_in": True, "user": session['user']})
    return jsonify({"logged_in": False})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(f"build/{path}"):
        return send_from_directory('build', path)
    return send_from_directory('build', 'index.html')

# Cleanup on App Termination
def cleanup(signum, frame):
    camera.stop()
    #release_video_stream()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)   # Handle Ctrl+C
signal.signal(signal.SIGTERM, cleanup)  # Handle termination

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
