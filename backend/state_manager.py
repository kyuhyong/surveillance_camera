import cv2
import multiprocessing
import time
import json
import os

STATE_FILE = "system_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as file:
            return json.load(file)
    return {"isArmed": False, "motion_sensitivity": 3}  # Default values

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
