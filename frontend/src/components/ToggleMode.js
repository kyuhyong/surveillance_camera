import React, { useState, useEffect } from 'react';
import { FaCog } from 'react-icons/fa'; // Gear Icon

export default function ToggleMode() {
    const [showSettings, setShowSettings] = useState(false); // State for expanded panel
    const [isArmed, setIsArmed] = useState(false);
    const [sendNotification, setSendNotification] = useState(false);
    const [sensitivity, setSensitivity] = useState(3);  // Default sensitivity level

    // Load settings on initial page load
    useEffect(() => {
        const loadSettings = async () => {
            try {
                const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/get_settings`);
                const data = await response.json();

                setIsArmed(data.isArmed);
                setSensitivity(data.motion_sensitivity);
            } catch (error) {
                console.error('Error fetching settings:', error);
            }
        };

        loadSettings();
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
            <div style={styles.mainContent}>
                <h3>Camera Mode: <b>{isArmed ? 'ARMED' : 'DISARMED'}</b></h3>
                {/* Gear Icon for Settings */}
                    <h3>Settings: </h3><FaCog
                    style={styles.gearIcon}
                    onClick={() => setShowSettings(!showSettings)}
                />
            </div>

            {/* Expandable Settings Panel */}
            {showSettings && (
                <div style={styles.settingsPanel}>
                    {/* ARM/DISARM */}
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
                    </div>
                    {/* Notification Checkbox */}
                    <div style={styles.checkboxContainer}>
                        <label htmlFor="notification">Send Notification : </label>
                        <input
                            type="checkbox"
                            id="notification"
                            checked={sendNotification}
                            onChange={handleNotificationChange}
                            style={styles.largeCheckbox}  // Increased size
                        />    
                    </div>
                    {/* Motion Sensitivity Slider */}
                    <div style={styles.sliderContainer}>
                        <label htmlFor="sensitivity">Motion Sensitivity :</label>
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
            )}
        </div>
    );
}

const styles = {
    container: {
        backgroundColor: '#d1d1d1', // Light grey background for the header
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '10px',
        margin: '1px 0'
    },
    mainContent: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: '70%',
        gap: '10px'
    },
    gearIcon: {
        cursor: 'pointer',
        fontSize: '24px',
        color: '#363636',
        marginLeft: '10px'
    },
    settingsPanel: {
        width: '95%',
        backgroundColor: '#efe',
        border: '2px solid #ddd',
        borderRadius: '10px',
        padding: '5px',
        marginTop: '5px',
        marginBottom: '10px',
        boxShadow: '10px 4px 8px rgba(0, 0, 0, 0.1)'
    },
    toggleContainer: {
        display: 'flex',
        alignItems: 'center',         // Align ARM/DISARM + Checkbox horizontally
        gap: '15px',                  // Adds spacing between items
        width: '100%',
        justifyContent: 'center'
    },
    toggleButton: {
        width: '40%',              // Set to 50% width
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
        gap: '20px'
    },
    sliderContainer: {
        display: 'flex',
        alignItems: 'center',
        gap: '80px'
    },
    largeCheckbox: {
        transform: 'scale(2)',  // Enlarges the checkbox
        cursor: 'pointer'
    },
    slider: {
        width: '200px',
        cursor: 'pointer'
    }
};