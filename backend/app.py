#!/usr/bin/env python

from flask import Flask, request, jsonify, send_file, Response, session
from flask import send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_session import Session
from flask_socketio import SocketIO, emit
import logging, os, cv2, threading, time
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS
import config
import threading
# To store armed state into json file
from state_manager import get_armed_status, set_armed_status, get_motion_sensitivity, set_motion_sensitivity
import multiprocessing
from detector_service import detector_service  # Import function from `detector_service.py`

load_dotenv()

# Initialize Flask app and SocketIO
app = Flask(__name__, static_folder='build')
socketio = SocketIO(app, cors_allowed_origins="*")

# Queue to receive frames from `detector_service.py`
frame_queue = multiprocessing.Queue(maxsize=10)
notification_queue = multiprocessing.Queue(maxsize=5)

# Start detector process
detector_process = multiprocessing.Process(target=detector_service, args=(frame_queue, notification_queue))
detector_process.start()

# Suppress Flask's default HTTP request logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # Suppress non-critical logs

# Flask Session Configuration
app.secret_key = 'super-secret-key'  # Required for session security
app.config['SESSION_TYPE'] = 'filesystem'  # Store session data on the server
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session expiry in seconds (e.g., 1 hour)
Session(app)  # Initialize Flask-Session
external_ip = os.getenv('EXTERNAL_IP')
print(f"External IP: {external_ip}")
CORS(app)
#CORS(app, origins=['http://'+external_ip+':3000'])
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

# Thread to read notifications and broadcast to frontend
def notify_frontend():
    print("Notification thread started!")
    while True:
        try:
            if not notification_queue.empty():
                clip_info = notification_queue.get(timeout=5)
                socketio.emit('new_clip', clip_info)
        except multiprocessing.queues.Empty:
            pass  # No new clips yet, continue waiting
        time.sleep(1)

# Start background notification thread
threading.Thread(target=notify_frontend, daemon=True).start()

@app.route('/api/video_stream')
def video_stream():
    # Get frame in the queue received from 'detector_service.py'
    def generate_video_stream():
        while True:
            try:
                if not frame_queue.empty():
                    frame = frame_queue.get()
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()

                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                print(f"❌ Error fetching frame from queue: {e}")

    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Endpoint to get current settings
@app.route('/api/get_settings', methods=['GET'])
def get_settings():
    return jsonify({
        # Fetch from state stored in json file
        "isArmed": get_armed_status(), #isArmed,
        "motion_sensitivity": get_motion_sensitivity() #motion_sensitivity
    })

@app.route('/api/toggle_mode', methods=['POST'])
def toggle_mode():
    #global isArmed
    data = request.json
    isArmed = data.get('isArmed', False)
    # Store current armed state
    set_armed_status(isArmed)
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
    #global motion_sensitivity
    data = request.json
    motion_sensitivity = data.get('sensitivity', 3)
    set_motion_sensitivity(motion_sensitivity)
    print(f"🎯 Motion detection sensitivity set to: {motion_sensitivity}")
    return jsonify({"message": f"Sensitivity set to {motion_sensitivity}"})

@app.route('/api/clips')
def get_clips():
    """List recorded motion-detected clips"""
    clips = []
    # Collect both video and image data
    for video_file in os.listdir(config.CLIPS_FOLDER):
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
        return send_from_directory(config.IMAGES_FOLDER, filename, mimetype='image/jpeg')
    except FileNotFoundError:
        abort(404, description="Image not found")

# Serve Videos with Streaming Support
@app.route('/api/video/<string:filename>')
def view_video(filename):
    video_path = os.path.join(config.STREAM_FOLDER, filename)

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

@app.route('/api/download_clip/<string:filename>')
def download_clip(filename):
    video_path = os.path.join(config.CLIPS_FOLDER, filename)

    if not os.path.exists(video_path):
        abort(404, description="Video file not found")

    return send_file(video_path, as_attachment=True)

@app.route('/api/delete_clip/<string:filename>', methods=['DELETE'])
def delete_clip(filename):
    """Delete recorded video"""
    try:
        os.remove(os.path.join(config.CLIPS_FOLDER, filename))
        os.remove(os.path.join(config.STREAM_FOLDER, filename))
        image_filename = filename.replace('.mp4','.jpg').replace('motion','image')
        #print(f"DELETE: image_filename={image_filename}")
        os.remove(os.path.join(config.IMAGES_FOLDER, image_filename))
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
