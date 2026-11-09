import React, { useState, useEffect } from 'react';
import { FaChevronDown, FaShieldAlt, FaPowerOff } from 'react-icons/fa';
import { API_BASE_URL } from '../config';

const SENSITIVITY_LABELS = ['', 'Very low', 'Low', 'Medium', 'High', 'Very high'];

async function postJson(path, body) {
    const res = await fetch(`${API_BASE_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json().catch(() => ({}));
}

// Percentage of the slider track to fill (used by the WebKit track gradient)
const fill = (value, min, max) => ({ '--fill': `${((value - min) / (max - min)) * 100}%` });

export default function ToggleMode({ onArmedChange = () => {}, notify = () => {} }) {
    const [showSettings, setShowSettings] = useState(false);
    const [isArmed, setIsArmed] = useState(false);
    const [busy, setBusy] = useState(false);
    const [sendNotification, setSendNotification] = useState(false);
    const [sensitivity, setSensitivity] = useState(3);
    const [duration, setDuration] = useState(5); // recording length in seconds

    useEffect(() => {
        const loadSettings = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/get_settings`);
                const data = await response.json();
                setIsArmed(!!data.isArmed);
                onArmedChange(!!data.isArmed);
                if (data.motion_sensitivity) setSensitivity(data.motion_sensitivity);
                if (data.detection_duration) setDuration(data.detection_duration);
            } catch (error) {
                console.error('Error fetching settings:', error);
                notify('Could not load camera settings', 'error');
            }
        };
        loadSettings();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleToggle = async () => {
        const newState = !isArmed;
        setBusy(true);
        try {
            await postJson('/api/toggle_mode', { isArmed: newState });
            setIsArmed(newState);
            onArmedChange(newState);
            notify(newState ? 'Camera armed: motion will be recorded' : 'Camera disarmed');
        } catch (err) {
            notify('Failed to change camera mode', 'error');
        } finally {
            setBusy(false);
        }
    };

    // Save sensitivity / duration once the slider is released, not on every drag step
    const saveSensitivity = async (event) => {
        try {
            await postJson('/api/set_sensitivity', { sensitivity: Number(event.target.value) });
        } catch (err) {
            notify('Failed to save sensitivity', 'error');
        }
    };

    const saveDuration = async (event) => {
        try {
            await postJson('/api/set_detection_duration', { duration: Number(event.target.value) });
        } catch (err) {
            notify('Failed to save recording duration', 'error');
        }
    };

    const handleNotificationChange = async () => {
        const newValue = !sendNotification;
        setSendNotification(newValue);
        try {
            await postJson('/api/set_notification', { sendNotification: newValue });
        } catch (err) {
            setSendNotification(!newValue);
            notify('Failed to save notification setting', 'error');
        }
    };

    return (
        <section className="card">
            <div className="card-body">
                <div className="arm-row">
                    <div className="arm-status">
                        <div className={`arm-icon ${isArmed ? 'armed' : 'disarmed'}`}>
                            <FaShieldAlt />
                        </div>
                        <div>
                            <strong>{isArmed ? 'Armed' : 'Disarmed'}</strong>
                            <span className="muted">
                                {isArmed ? 'Recording when motion is detected' : 'Motion recording is off'}
                            </span>
                        </div>
                    </div>
                    <button
                        className={`btn ${isArmed ? 'btn-ghost' : 'btn-danger'}`}
                        onClick={handleToggle}
                        disabled={busy}
                    >
                        <FaPowerOff size={14} />
                        {isArmed ? 'Disarm' : 'Arm'}
                    </button>
                </div>
            </div>

            <button
                className={`settings-toggle ${showSettings ? 'open' : ''}`}
                onClick={() => setShowSettings(!showSettings)}
                aria-expanded={showSettings}
                aria-controls="camera-settings"
            >
                Detection settings
                <FaChevronDown className="chev" />
            </button>

            {showSettings && (
                <div className="settings" id="camera-settings">
                    <div className="setting">
                        <div className="setting-head">
                            <div>
                                <label htmlFor="notification">Notifications</label>
                                <div className="setting-desc">Send an alert when motion is recorded</div>
                            </div>
                            <span className="switch">
                                <input
                                    type="checkbox"
                                    id="notification"
                                    role="switch"
                                    checked={sendNotification}
                                    onChange={handleNotificationChange}
                                />
                                <span className="track" />
                            </span>
                        </div>
                    </div>

                    <div className="setting">
                        <div className="setting-head">
                            <label htmlFor="sensitivity">Motion sensitivity</label>
                            <span className="setting-value">{SENSITIVITY_LABELS[sensitivity] || sensitivity}</span>
                        </div>
                        <input
                            className="range"
                            type="range"
                            id="sensitivity"
                            min="1"
                            max="5"
                            step="1"
                            value={sensitivity}
                            style={fill(sensitivity, 1, 5)}
                            onChange={(e) => setSensitivity(Number(e.target.value))}
                            onPointerUp={saveSensitivity}
                            onKeyUp={saveSensitivity}
                        />
                        <div className="range-labels"><span>Less</span><span>More</span></div>
                    </div>

                    <div className="setting">
                        <div className="setting-head">
                            <label htmlFor="duration">Recording length</label>
                            <span className="setting-value">{duration}s</span>
                        </div>
                        <input
                            className="range"
                            type="range"
                            id="duration"
                            min="5"
                            max="30"
                            step="1"
                            value={duration}
                            style={fill(duration, 5, 30)}
                            onChange={(e) => setDuration(Number(e.target.value))}
                            onPointerUp={saveDuration}
                            onKeyUp={saveDuration}
                        />
                        <div className="range-labels"><span>5s</span><span>30s</span></div>
                    </div>
                </div>
            )}
        </section>
    );
}
