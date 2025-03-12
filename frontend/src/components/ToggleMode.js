import React, { useState, useEffect } from 'react';

export default function ToggleMode() {
    const [isArmed, setIsArmed] = useState(false);
    const [sensitivity, setSensitivity] = useState(3);  // Default sensitivity level
    const [sendNotification, setSendNotification] = useState(false);

    useEffect(() => {
        // Fetch current camera mode on load
        fetch(`${process.env.REACT_APP_API_BASE_URL}/api/get_mode`)
            .then(res => res.json())
            .then(data => setIsArmed(data.mode === 'ARMED'));
    }, []);

    const handleToggle = async () => {
        const newState = !isArmed;
        setIsArmed(newState);

        await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/toggle_mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ isArmed: newState })
        });
    };
    // Change Sensitivity
    const handleSensitivityChange = async (event) => {
        const newSensitivity = Number(event.target.value);
        setSensitivity(newSensitivity);

        await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/set_sensitivity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sensitivity: newSensitivity })
        });
    };
    // Toggle Notification Checkbox
    const handleNotificationChange = async () => {
        const newNotificationState = !sendNotification;
        setSendNotification(newNotificationState);

        await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/set_notification`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sendNotification: newNotificationState })
        });
    };

    return (
        <div style={styles.container}>
            {/*<h3>Camera Mode: {isArmed ? 'ARMED' : 'DISARMED'}</h3>*/}
            <p>Camera Mode: <b>{isArmed ? 'ARMED' : 'DISARMED'}</b></p>
            {/* ARM/DISARM + Checkbox Side by Side */}
            <div style={styles.toggleContainer}>
                <button 
                    style={{
                        ...styles.toggleButton,
                        backgroundColor: isArmed ? '#f44336' : '#4CAF50' // Red for ARMED, Green for DISARMED
                    }}
                    onClick={handleToggle}
                >
                    {isArmed ? 'Disarm' : 'Arm'}
                </button>
                {/* Notification Checkbox */}
                <div style={styles.checkboxContainer}>
                    <input
                        type="checkbox"
                        id="notification"
                        checked={sendNotification}
                        onChange={handleNotificationChange}
                    />
                    <label htmlFor="notification">Send Notification</label>
                </div>
            </div>
            {/* Motion Sensitivity Slider */}
            <div style={styles.sensitivityContainer}>
                <label htmlFor="sensitivity">Motion Sensitivity:</label>
                <input
                    type="range"
                    id="sensitivity"
                    min="1"
                    max="5"
                    value={sensitivity}
                    onChange={handleSensitivityChange}
                    style={styles.slider}
                />
                <span>{sensitivity}</span>
            </div>
        </div>
    );
}

const styles = {
    container: {
        backgroundColor: '#d1d1d1', // Light grey background for the header
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1px',
        margin: '1px 0'
    },
    toggleContainer: {
        display: 'flex',
        alignItems: 'center',         // Align ARM/DISARM + Checkbox horizontally
        gap: '15px',                  // Adds spacing between items
        width: '100%',
        justifyContent: 'center'
    },
    toggleButton: {
        width: '50%',              // Set to 50% width
        color: 'white',
        border: 'none',
        padding: '10px',
        borderRadius: '10px',
        cursor: 'pointer',
        transition: 'background-color 0.2s ease'
    },
    checkboxContainer: {
        display: 'flex',
        alignItems: 'center',
        gap: '5px'
    },
    sensitivityContainer: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px'
    },
    slider: {
        width: '200px',
        cursor: 'pointer'
    }
};