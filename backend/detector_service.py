#!/usr/bin/env python

import json
import time
import cv2
import numpy as np
from camera import Camera
import logging, os, signal, sys, cv2, threading, time, subprocess
from datetime import datetime
import multiprocessing
import time
import config
import threading
from rpi_handler import RpiHandler

ARMED_FILE = 'system_state.json'

# Path to save motion-detected videos
#CLIPS_FOLDER = 'recorded_clips'
os.makedirs(config.CLIPS_FOLDER, exist_ok=True)
#STREAM_FOLDER = 'stream_clips'
os.makedirs(config.STREAM_FOLDER, exist_ok=True)
#IMAGES_FOLDER = 'recorded_images'
os.makedirs(config.IMAGES_FOLDER, exist_ok=True)

# Motion detection settings
FRAME_DELAY = 1.0 / config.TARGET_FPS  # Delay to match target FPS
print(f"FPS={config.TARGET_FPS}, DELAY={FRAME_DELAY}")
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
rpi = RpiHandler()
notifier = None

def check_json():
    try:
        with open(ARMED_FILE, 'r') as f:
            state = json.load(f)
            return state["isArmed"], state["motion_sensitivity"]
    except FileNotFoundError:
        return False, 3

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

def detector_service(frame_queue, notification_queue):
    global is_recording, v_writer, recording_timer, \
        recorded_video_path, last_motion_check, isArmed, \
        motion_count, brightness, motion_sensitivity, detection_ready_cnt, notifier
    notifier = notification_queue
    position = (10, 30)  # Position to place the text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (0, 255, 0)  # Green color in BGR
    thickness = 2
    camera.start()
    
    while True:
        # get frame from camera
        frame = camera.get_frame()
        if frame is not None:
            motion_detected = False

            # Check for motion every 0.5 seconds
            current_time = time.time()
            if current_time - last_motion_check >= 0.5:
                isArmed, motion_sensitivity = check_json()
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
            
            # Overlay the text on the frame
            cv2.putText(frame, current_time, position, font, font_scale, color, thickness)
            
            # Start recording when motion is detected
            if motion_detected and isArmed:
                if not is_recording:
                    is_recording = True
                    start_recording(frame)

            # Record images to video
            if is_recording and v_writer is not None:
                try:
                    v_writer.write(frame)
                except Exception as e:
                    print(f"❌ Error writing video: {e}")

            # Stop recording if switching to DISARMED
            if not isArmed and is_recording:
                stop_recording()
                
            # Label onscreen message
            txt = ("REC " if is_recording else ("ARMED" if isArmed else "DISARMED") )+"Motion:"+str(motion_count)+" @"+str(detection_ready_cnt)
            cv2.putText(frame, txt, (10, 60), font, font_scale, color, thickness)
            txt = "Brightness:"+str(brightness)
            cv2.putText(frame, txt, (10, 90), font, font_scale, color, thickness)
            
            # Encode frame for live streaming
            #_, buffer = cv2.imencode('.jpg', frame)
            #frame_bytes = buffer.tobytes()

            # Add the latest frame to the queue (drop old frames if overloaded)
            if not frame_queue.full():
                frame_queue.put(frame.copy())

def save_first_frame(frame, timestamp):
    """Save the first detected frame as an image"""
    image_path = os.path.join(config.IMAGES_FOLDER, f'image_{timestamp}.jpg')
    cv2.imwrite(image_path, frame)

def start_recording(frame):
    global v_writer, recorded_video_path, recording_timer
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    video_path = os.path.join(config.CLIPS_FOLDER, f'motion_{timestamp}.mp4')
    print(f"🎥 Motion detected : {video_path}")
    recorded_video_path = video_path
    save_first_frame(frame, timestamp)
    #fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    v_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (config.IMAGE_WIDTH, config.IMAGE_HEIGHT))
    # Start a timer to stop recording after a set duration
    if recording_timer:
        recording_timer.cancel()  # Cancel any active timer
    recording_timer = threading.Timer(config.DETECTION_DURATION, stop_recording)
    recording_timer.start()

def stop_recording():
    """Stop recording safely with proper resource cleanup"""
    global is_recording, v_writer, recorded_video_path, notifier
    if is_recording:
        if v_writer is not None:   # Safely release the VideoWriter
            v_writer.release()
            v_writer = None

        # Convert mp4 video to web-compatible format
        filename = os.path.basename(recorded_video_path)
        converted_path = os.path.join(config.STREAM_FOLDER, filename)
        convert_to_web_compatible(recorded_video_path, converted_path)
        is_recording = False
        timestamp_str = '_'.join(filename.split('_')[1:3]).replace('.mp4','')
        
        # Format timestamp for display (e.g., "2025-03-11 23:46:30")
        formatted_timestamp = timestamp_str.replace('_', ' ')
        image_filename = filename.replace('.mp4','.jpg').replace('motion','image')

        print(f"🛑 Stopping recording : {datetime.now()}")
        if notifier is not None:
            notifier.put({"timestamp":formatted_timestamp, "image_filename": image_filename, "video_filename": filename})

def convert_to_web_compatible(input_path, output_path):
    """Converts recorded video to web-compatible `.mp4` format"""
    try:
        if config.USE_PICAMERA:
            subprocess.run([
                'ffmpeg', '-i', input_path,
                '-c:v', 'libx264',
                '-crf', '23',
                '-r', '20',
                '-vsync', '1',
                '-hide_banner', '-loglevel','error',
                '-preset', 'ultrafast',
                '-movflags', '+faststart',
                output_path
            ], check=True)
        else:
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

# Auto-delete function
def auto_delete_old_clips():
    print(f"AUTO DELETE STARTED!")
    while True:
        now = datetime.now()
        for filename in os.listdir(config.CLIPS_FOLDER):
            file_path = os.path.join(config.CLIPS_FOLDER, filename)
            if os.path.isfile(file_path):
                # Extract the date from the filename
                try:                  
                    date_str = '_'.join(filename.split('_')[1:3]).split('.')[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
                    # Calculate file age
                    if (now - file_date).days > config.RETENTION_DAYS:
                        os.remove(file_path)
                        print(f"🗑️ Deleted old clip: {filename}")
                except (IndexError, ValueError):
                    print(f"❗ Invalid filename format: {filename}")
        
        # Check for old files every 24 hours
        time.sleep(24 * 3600)  # 86400 seconds = 1 day

# Start the auto-delete function in a separate thread
threading.Thread(target=auto_delete_old_clips, daemon=True).start()

# Cleanup on App Termination
def cleanup(signum, frame):
    camera.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)   # Handle Ctrl+C
signal.signal(signal.SIGTERM, cleanup)  # Handle termination

if __name__ == "__main__":
    frame_queue = multiprocessing.Queue(maxsize=10)  # Shared frame queue
    notification_queue = multiprocessing.Queue(maxsize=5)
    detector_process = multiprocessing.Process(target=detector_service, args=(frame_queue, notification_queue))
    detector_process.start()