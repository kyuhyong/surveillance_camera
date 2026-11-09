#!/usr/bin/env python

import json
import time
import cv2
import numpy as np
from camera import Camera
import logging, os, signal, sys, cv2, threading, time, subprocess
from datetime import datetime
import multiprocessing
import queue
import config
import threading
from rpi_handler import RpiHandler
from state_manager import clamp_detection_duration

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
# Motion is checked every 0.5s; treat motion as ongoing if seen within this window
MOTION_GRACE_PERIOD = 1.5

# Motion detection variables
isArmed = False     # Global state to manage ARM/DISARM mode
detection_ready_cnt = 0 # Detection readyness delay
prev_frame = None
last_motion_check = 0
motion_count = 0
brightness = 0
brightness_prev = 0
motion_sensitivity = 3
detection_duration = config.DETECTION_DURATION  # Recording length (s), set from the UI

v_stream = None   # VideoStream
camera = Camera(use_picamera=config.USE_PICAMERA)
is_recording = False
v_writer = None     # Video Writer
recording_timer = None  # Unused, kept for compatibility
recording_end_time = 0.0  # time.time() at which the current recording stops
recording_start_time = 0.0
recording_frames = 0      # Frames actually written to the current clip
recorded_video_path = ""
sendNotification = False # Notification state
rpi = RpiHandler()
notifier = None

def check_json():
    try:
        with open(ARMED_FILE, 'r') as f:
            state = json.load(f)
            duration = clamp_detection_duration(
                state.get("detection_duration", config.DETECTION_DURATION))
            return state["isArmed"], state["motion_sensitivity"], duration
    except (FileNotFoundError, ValueError, KeyError):
        # File missing or half-written by the web process; keep last known values
        return isArmed, motion_sensitivity, detection_duration

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

def detector_service(frame_queue, notification_queue, streaming_enabled_event, heartbeat=None):
    global is_recording, v_writer, recording_timer, \
        recorded_video_path, last_motion_check, isArmed, \
        motion_count, brightness, motion_sensitivity, detection_ready_cnt, notifier, \
        recording_frames, detection_duration
    notifier = notification_queue
    position = (10, 30)  # Position to place the text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (0, 255, 0)  # Green color in BGR
    thickness = 2
    signal.signal(signal.SIGINT, cleanup)   # Handle Ctrl+C
    signal.signal(signal.SIGTERM, cleanup)  # Handle terminate() from the supervisor
    print(f"📷 Detector PID {os.getpid()} starting camera...", flush=True)
    camera.start()
    print("📷 Camera started, waiting for frames", flush=True)
    if heartbeat is not None:
        heartbeat.value = time.time()
    got_first_frame = False
    empty_frames = 0
    last_motion_time = 0.0  # time.time() of the most recent motion detection

    try:
        while True:
            loop_start = time.time()
            # get frame from camera
            frame = camera.get_frame()
            if frame is None:
                # Don't busy-spin when the camera returns nothing. If this persists,
                # the heartbeat goes stale and the parent restarts this process.
                empty_frames += 1
                if empty_frames % 100 == 1:
                    print(f"⚠️ Camera returned no frame ({empty_frames} times)", flush=True)
                time.sleep(0.05)
                continue
            if not got_first_frame:
                got_first_frame = True
                print(f"✅ First frame received: {frame.shape}", flush=True)
            if heartbeat is not None:
                heartbeat.value = time.time()

            motion_detected = False

            # Check for motion every 0.5 seconds
            current_time = time.time()
            if current_time - last_motion_check >= 0.5:
                isArmed, motion_sensitivity, detection_duration = check_json()
                motion_count, brightness = check_motion(frame)
                # Check if image is bright enough to check detection
                if brightness > BRIGHTNESS_THREASHOLD:
                    if detection_ready_cnt > 2:
                        if motion_count > motion_sensitivity:
                            motion_detected = True
                    else:
                        detection_ready_cnt+=1
                else:
                    # Image is too dark for detection so reset count
                    detection_ready_cnt = 0

                last_motion_check = current_time

            # Overlay the current time on the frame
            cv2.putText(frame, datetime.now().strftime("%d/%m/%y, %H:%M:%S"),
                        position, font, font_scale, color, thickness)

            # Start recording when motion is detected
            if motion_detected and isArmed and not is_recording:
                start_recording(frame)

            # Record images to video
            if is_recording and v_writer is not None:
                try:
                    v_writer.write(frame)
                    recording_frames += 1
                except Exception as e:
                    print(f"❌ Error writing video: {e}")

            if motion_detected:
                last_motion_time = current_time

            # Stop recording when DISARMED, or once the configured duration is up
            # and no motion has been seen for MOTION_GRACE_PERIOD seconds (keep
            # recording while motion continues, up to MAX_RECORDING_DURATION).
            if is_recording:
                now = time.time()
                motion_ongoing = now - last_motion_time < MOTION_GRACE_PERIOD
                if (not isArmed
                        or (now >= recording_end_time and not motion_ongoing)
                        or now - recording_start_time >= config.MAX_RECORDING_DURATION):
                    stop_recording()

            # Label onscreen message
            txt = ("REC " if is_recording else ("ARMED" if isArmed else "DISARMED") ) \
                + " Motion: "+str(motion_count) \
                + "("+str(motion_sensitivity)+")"
            cv2.putText(frame, txt, (10, 60), font, font_scale, color, thickness)
            txt = "Brightness:"+str(brightness)
            cv2.putText(frame, txt, (10, 90), font, font_scale, color, thickness)

            # Send JPEG bytes (not raw frames) to the web process, only while
            # someone is watching. Drop the oldest frame if the queue is full so
            # the viewer always gets the most recent image.
            if streaming_enabled_event.is_set():
                ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    push_latest(frame_queue, buffer.tobytes())

            # Pace the loop to TARGET_FPS (instead of a fixed sleep on top of processing time)
            elapsed = time.time() - loop_start
            if elapsed < FRAME_DELAY:
                time.sleep(FRAME_DELAY - elapsed)
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        if is_recording:
            stop_recording()
        camera.stop()

def push_latest(q, item):
    """Put item into q, discarding the oldest entry if q is full."""
    try:
        q.put_nowait(item)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(item)
        except queue.Full:
            pass

def save_first_frame(frame, timestamp):
    """Save the first detected frame as an image"""
    image_path = os.path.join(config.IMAGES_FOLDER, f'image_{timestamp}.jpg')
    cv2.imwrite(image_path, frame)

RECORD_FPS = float(config.TARGET_FPS)  # Nominal FPS written into the raw clip header

def start_recording(frame):
    global v_writer, recorded_video_path, is_recording, \
        recording_end_time, recording_start_time, recording_frames
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    video_path = os.path.join(config.CLIPS_FOLDER, f'motion_{timestamp}.mp4')
    print(f"🎥 Motion detected : {video_path}")
    recorded_video_path = video_path
    save_first_frame(frame, timestamp)
    #fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    h, w = frame.shape[:2]
    v_writer = cv2.VideoWriter(video_path, fourcc, RECORD_FPS, (w, h))
    recording_start_time = time.time()
    recording_end_time = recording_start_time + detection_duration
    recording_frames = 0
    is_recording = True

def stop_recording():
    """Stop recording. Called only from the detector loop (no timer thread),
    so the writer is never released while a frame is being written."""
    global is_recording, v_writer, recorded_video_path
    if not is_recording:
        return
    is_recording = False
    if v_writer is not None:
        v_writer.release()
        v_writer = None

    duration = time.time() - recording_start_time
    actual_fps = recording_frames / duration if duration > 0 else RECORD_FPS
    print(f"🛑 Stopping recording : {datetime.now()} "
          f"({recording_frames} frames in {duration:.1f}s = {actual_fps:.1f} fps)")

    # Convert in the background so the live view keeps running
    threading.Thread(
        target=finish_recording,
        args=(recorded_video_path, actual_fps),
        daemon=True
    ).start()

def finish_recording(raw_path, actual_fps):
    filename = os.path.basename(raw_path)
    converted_path = os.path.join(config.STREAM_FOLDER, filename)
    convert_to_web_compatible(raw_path, converted_path, actual_fps)

    timestamp_str = '_'.join(filename.split('_')[1:3]).replace('.mp4','')
    # Format timestamp for display (e.g., "2025-03-11 23:46:30")
    formatted_timestamp = timestamp_str.replace('_', ' ')
    image_filename = filename.replace('.mp4','.jpg').replace('motion','image')
    if notifier is not None:
        try:
            notifier.put_nowait({"timestamp":formatted_timestamp, "image_filename": image_filename, "video_filename": filename})
        except queue.Full:
            pass

def convert_to_web_compatible(input_path, output_path, actual_fps=None):
    """Converts recorded video to web-compatible `.mp4` format.

    The raw clip is written with a nominal RECORD_FPS, but the Pi usually
    captures fewer frames per second than that, which makes playback too fast.
    Stretch the timestamps by RECORD_FPS / actual_fps so it plays in real time."""
    cmd = ['ffmpeg', '-y', '-i', input_path]
    if actual_fps and actual_fps > 0:
        scale = RECORD_FPS / actual_fps
        if abs(scale - 1.0) > 0.02:
            cmd += ['-vf', f'setpts={scale:.4f}*PTS']
    cmd += [
        '-c:v', 'libx264',
        '-crf', '23',
        '-r', str(int(RECORD_FPS)),
        '-vsync', '1',
        '-an',
        '-hide_banner', '-loglevel', 'error',
        '-preset', 'ultrafast' if config.USE_PICAMERA else 'fast',
        '-movflags', '+faststart',
        output_path
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Conversion successful: {output_path}")
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"❌ Conversion failed: {e}")

# Auto-delete function
def auto_delete_old_clips():
    print(f"AUTO DELETE STARTED!")
    while True:
        now = datetime.now()
        for folder in (config.CLIPS_FOLDER, config.STREAM_FOLDER, config.IMAGES_FOLDER):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if not os.path.isfile(file_path):
                    continue
                # Extract the date from the filename (motion_/image_YYYY-mm-dd_HH-MM-SS.ext)
                try:
                    date_str = '_'.join(filename.split('_')[1:3]).split('.')[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
                    if (now - file_date).days > config.RETENTION_DAYS:
                        os.remove(file_path)
                        print(f"🗑️ Deleted old file: {file_path}")
                except (IndexError, ValueError):
                    print(f"❗ Invalid filename format: {filename}")
                except OSError as e:
                    print(f"❗ Could not delete {file_path}: {e}")

        # Check for old files every hour
        time.sleep(3600)

# Start the auto-delete function in a separate thread
threading.Thread(target=auto_delete_old_clips, daemon=True).start()

# Cleanup on termination. Installed only inside the detector process: in the
# web process, calling sys.exit() from a signal handler while OpenCV/werkzeug
# threads are running caused a segfault on `systemctl stop`.
def cleanup(signum, frame):
    sys.exit(0)  # raises SystemExit in the loop; its `finally` stops the camera

if __name__ == "__main__":
    frame_queue = multiprocessing.Queue(maxsize=10)  # Shared frame queue
    notification_queue = multiprocessing.Queue(maxsize=5)
    streaming_enabled_event = multiprocessing.Event()
    detector_process = multiprocessing.Process(target=detector_service, args=(frame_queue, notification_queue, streaming_enabled_event))
    detector_process.start()