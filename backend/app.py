#!/usr/bin/env python

from flask import Flask, request, jsonify, send_file, Response, session
from flask import render_template_string, redirect, url_for     # For block IP
from flask import send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_session import Session
from flask_socketio import SocketIO, emit
import logging, os, cv2, threading, time, queue
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_cors import CORS
import config
import threading
# To store armed state into json file
from state_manager import get_armed_status, set_armed_status, get_motion_sensitivity, set_motion_sensitivity
import multiprocessing
from detector_service import detector_service  # Import function from `detector_service.py`
import requests
import time

load_dotenv()

# Frontend build served by Flask. Prefer the fresh `npm run build` output in
# frontend/build; fall back to the old backend/build copy if that's all there is.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_BUILD_DIR = os.path.join(BACKEND_DIR, '..', 'frontend', 'build')
if not os.path.isdir(FRONTEND_BUILD_DIR):
    FRONTEND_BUILD_DIR = os.path.join(BACKEND_DIR, 'build')
FRONTEND_BUILD_DIR = os.path.abspath(FRONTEND_BUILD_DIR)
print(f"Serving frontend from: {FRONTEND_BUILD_DIR}")

# Initialize Flask app and SocketIO (static files are served by serve_frontend)
app = Flask(__name__, static_folder=None)

# Suppress Flask's default HTTP request logs
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# Secret key (SET ONCE)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

def detect_lan_ip():
    """Best-effort LAN IP of this machine (no packets are actually sent)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None

external_ip = os.getenv("EXTERNAL_IP")  # optional: public IP / DNS name used from outside
lan_ip = detect_lan_ip()
print(f"External IP: {external_ip}, LAN IP: {lan_ip}")

# Origins allowed to call the API / socket.io from a browser. Covers the page
# being served by Flask itself (:5000) and the React dev server / `serve` (:3000).
import socket as _socket
_hosts = {"localhost", "127.0.0.1", _socket.gethostname(), f"{_socket.gethostname()}.local"}
for _h in (external_ip, lan_ip):
    if _h:
        _hosts.add(_h)
allowed_origins = [f"http://{h}:{port}" for h in sorted(_hosts) for port in (3000, 5000)]
print(f"Allowed origins: {allowed_origins}")

from flask_cors import CORS
CORS(
    app,
    supports_credentials=True,
    origins=allowed_origins
)

socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    manage_session=False
)

# Session config
app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=3600,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)

Session(app)

# Database (ONE source of truth)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.getenv("DATABASE_URL") or "sqlite:///login_attempts.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Mail
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSKEY")
)
mail = Mail(app)

sendNotification = False # Notification state

# Queue to receive frames from `detector_service.py`
# Holds encoded JPEG bytes; kept small so frames never pile up in memory
frame_queue = multiprocessing.Queue(maxsize=2)
notification_queue = multiprocessing.Queue(maxsize=50)
# Shared event flag: set while at least one client is watching the live stream
streaming_enabled_event = multiprocessing.Event()
# Updated by the detector on every good frame; used to detect a hung camera
# lock=False: the detector may be killed at any moment; a lock held by a killed
# process would deadlock the next detector and the supervisor.
detector_heartbeat = multiprocessing.Value('d', 0.0, lock=False)
DETECTOR_STALL_TIMEOUT = 30  # seconds without a frame before restarting the detector

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



ATTEMPT_LIMIT = 3
BLOCK_DURATION_MINUTES = 5

class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    blocked_until = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<LoginAttempt {self.ip_address} {self.attempts} {self.blocked_until}>"

def get_or_create_attempt(ip: str) -> LoginAttempt:
    record = LoginAttempt.query.filter_by(ip_address=ip).first()
    if not record:
        record = LoginAttempt(ip_address=ip, attempts=0, blocked_until=None)
        db.session.add(record)
        db.session.commit()
    return record

def is_blocked(ip: str) -> bool:
    record = LoginAttempt.query.filter_by(ip_address=ip).first()
    if not record or not record.blocked_until:
        return False
    if datetime.utcnow() < record.blocked_until:
        return True
    # If block expired, reset
    record.blocked_until = None
    record.attempts = 0
    db.session.commit()
    return False

def start_detector_process():
    """서브프로세스 실행 함수"""
    process = multiprocessing.Process(
        target=detector_service, 
        args=(frame_queue, notification_queue, streaming_enabled_event, detector_heartbeat),
        # Daemon: if the web server dies, the main process exits immediately and
        # systemd restarts everything, instead of hanging while waiting on the child.
        daemon=True
    )
    detector_heartbeat.value = time.time()  # startup grace period
    process.start()
    logging.info(f"Started detector process PID: {process.pid}")
    return process

def run_detector_process():
    detector_process = start_detector_process()
    #logging.info(f"Started detector process PID: {process.pid}")
    try:
        while True:
            # 비정상 종료된 경우 자동 재시작
            if not detector_process.is_alive():
                logging.warning(f"Detector process PID: {detector_process.pid} exited with code {detector_process.exitcode}. Restarting...")
                detector_process.join(timeout=1)
                detector_process = start_detector_process()
            elif time.time() - detector_heartbeat.value > DETECTOR_STALL_TIMEOUT:
                # Process is alive but no frames (camera hung / disconnected)
                logging.warning(f"Detector process PID: {detector_process.pid} stalled "
                                f"(no frame for {DETECTOR_STALL_TIMEOUT}s). Restarting...")
                detector_process.terminate()
                detector_process.join(timeout=5)
                if detector_process.is_alive():
                    detector_process.kill()
                    detector_process.join(timeout=5)
                time.sleep(2)  # let the camera device be released
                detector_process = start_detector_process()

            # 주기적으로 데이터 추가 (테스트용)
            #frame_queue.put("Sample Frame Data")
            time.sleep(5)

    except KeyboardInterrupt:
        logging.warning("Main process interrupted. Terminating gracefully...")

    finally:
        # 종료 처리
        if detector_process.is_alive():
            detector_process.terminate()
            detector_process.join()
        logging.info(f"Detector process PID: {detector_process.pid} terminated.")

# Start detector process thread
threading.Thread(target=run_detector_process, daemon=True).start()

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

# ---------------------------------------------------------------------------
# Live stream
# A single reader thread pulls JPEG frames from the detector and publishes the
# latest one. Every viewer reads that shared frame, so multiple/stale clients
# no longer steal frames from each other.
# ---------------------------------------------------------------------------
_frame_cond = threading.Condition()
_latest_frame = None
_frame_id = 0
_viewer_lock = threading.Lock()
_viewer_count = 0

def frame_reader():
    global _latest_frame, _frame_id
    while True:
        try:
            data = frame_queue.get(timeout=1.0)
        except queue.Empty:
            continue
        except Exception as e:
            logging.warning(f"Frame reader error: {e}")
            time.sleep(1)
            continue
        with _frame_cond:
            _latest_frame = data
            _frame_id += 1
            _frame_cond.notify_all()

threading.Thread(target=frame_reader, daemon=True).start()

def _viewer_joined():
    global _viewer_count
    with _viewer_lock:
        _viewer_count += 1
        streaming_enabled_event.set()

def _viewer_left():
    global _viewer_count, _latest_frame
    with _viewer_lock:
        _viewer_count = max(0, _viewer_count - 1)
        if _viewer_count == 0:
            streaming_enabled_event.clear()
            with _frame_cond:
                _latest_frame = None  # don't show a stale frame to the next viewer

@app.route('/api/video_stream')
def video_stream():
    def generate_video_stream():
        _viewer_joined()
        try:
            last_id = -1
            last_sent = 0.0
            while True:
                with _frame_cond:
                    _frame_cond.wait_for(lambda: _frame_id != last_id, timeout=1.0)
                    fid, frame_bytes = _frame_id, _latest_frame
                if frame_bytes is None:
                    continue
                now = time.time()
                # Send new frames; if none arrive, resend the last one every second.
                # The resend acts as a keepalive and makes a dead client connection
                # raise an error, so this generator exits instead of leaking.
                if fid == last_id and now - last_sent < 1.0:
                    continue
                last_id = fid
                last_sent = now
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
                       + frame_bytes + b'\r\n')
        finally:
            _viewer_left()

    return Response(generate_video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})

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

# Serve Videos (send_file with conditional=True handles HTTP Range requests)
@app.route('/api/video/<string:filename>')
def view_video(filename):
    video_path = os.path.join(config.STREAM_FOLDER, os.path.basename(filename))
    if not os.path.exists(video_path):
        abort(404, description="Video file not found")
    return send_file(video_path, mimetype='video/mp4', conditional=True)

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

@app.route('/api/user_login', methods=['POST'])
def login():
    import time
    
    # Check if this IP is blocked
    ip = request.remote_addr
    if is_blocked(ip):
        return jsonify({"error": "Your IP is temporarily blocked due to too many failed attempts."}), 403
    
    attempt_record = get_or_create_attempt(ip)

    data = request.json
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    username = data.get('username')
    if user:
        session['user'] = username # Store user in session
        session.permanent = True  # Ensures persistent session
        # Successful login
        attempt_record.attempts = 0
        attempt_record.blocked_until = None
        db.session.commit()
        return jsonify({"message": "Login successful", "status": "success"})
    else :
        # Failed login
        attempt_record.attempts += 1
        if attempt_record.attempts >= ATTEMPT_LIMIT:
            attempt_record.blocked_until = datetime.utcnow() + timedelta(minutes=BLOCK_DURATION_MINUTES)
        db.session.commit()
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    print("🔒 User logged out")
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
    if path and os.path.isfile(os.path.join(FRONTEND_BUILD_DIR, path)):
        return send_from_directory(FRONTEND_BUILD_DIR, path)
    # index.html must not be cached, otherwise browsers keep loading an old build
    response = send_from_directory(FRONTEND_BUILD_DIR, 'index.html')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route("/ping")
def ping():
    return {"ok": True}

# 로깅 설정
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

if __name__ == "__main__":


    # Start detector process
    #detector_process = multiprocessing.Process(
    #    target=detector_service, 
    #    args=(frame_queue, notification_queue)
    #)
    #detector_process.start()
    #logging.info(f"Started detector process PID: {detector_process.pid}")

    with app.app_context():
        db.create_all()
    #app.run(host='0.0.0.0', port=5000, debug=False) #Do not use app.run
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False,
        # Flask-SocketIO refuses to start Werkzeug when there is no terminal
        # (e.g. under systemd). Werkzeug's threaded server is fine for a
        # single-camera LAN app.
        allow_unsafe_werkzeug=True
    )
