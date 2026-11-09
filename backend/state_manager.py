import cv2
import multiprocessing
import time
import json
import os
import config

STATE_FILE = "system_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as file:
            return json.load(file)
    return {"isArmed": False, "motion_sensitivity": 3,
            "detection_duration": config.DETECTION_DURATION}  # Default values

def save_state(state):
    with open(STATE_FILE, 'w') as file:
        json.dump(state, file)

# Global state variable (loaded from file)
state = load_state()

def get_armed_status():
    return state["isArmed"]

def set_armed_status(value):
    state["isArmed"] = value
    save_state(state)

def get_motion_sensitivity():
    return state["motion_sensitivity"]

def set_motion_sensitivity(value):
    state["motion_sensitivity"] = value
    save_state(state)

DETECTION_DURATION_MIN = 5
DETECTION_DURATION_MAX = 30

def clamp_detection_duration(value):
    """Recording length in seconds, limited to the range the UI allows."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return config.DETECTION_DURATION
    return max(DETECTION_DURATION_MIN, min(DETECTION_DURATION_MAX, value))

def get_detection_duration():
    return clamp_detection_duration(state.get("detection_duration", config.DETECTION_DURATION))

def set_detection_duration(value):
    state["detection_duration"] = clamp_detection_duration(value)
    save_state(state)
    return state["detection_duration"]
