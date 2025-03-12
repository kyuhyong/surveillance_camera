import React from 'react';
import { useNavigate } from 'react-router-dom';
import LiveStream from './LiveStream';
import ToggleMode from './ToggleMode';
import ClipsList from './ClipsList';
import { FaSignOutAlt } from 'react-icons/fa';  // Import Logout Icon

export default function Dashboard() {
    const navigate = useNavigate();

    const handleLogout = async () => {
        await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/logout`, { method: 'POST' });
        localStorage.removeItem('isLoggedIn');  // Clear session in frontend
        alert('Logged out successfully!');
        navigate('/login');  // Redirect to login page
    };
    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h1>Surveillance System Dashboard</h1>
                {/* Logout Button with Icon */}
                <button onClick={handleLogout} style={styles.logoutButton} title="Logout">
                    <FaSignOutAlt size={25} />
                </button>
            </div>
            <div style={styles.content}>
                <LiveStream />
                <ToggleMode />
                <ClipsList />
            </div>
        </div>
    );
}

const styles = {
    container: {
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',          // Full viewport height
        overflow: 'hidden',        // Prevents unnecessary overflow
    },
    header: {
        backgroundColor: '#969696', // Light grey background for the header
        color: 'white',
        padding: '8px',
        position: 'sticky',
        top: 0,
        zIndex: 10,
        display: 'flex',
        justifyContent: 'space-between',  // Header items spread out
        alignItems: 'center',
        marginTop: '1px',         // Smaller top margin
        height: '85px'
    },
    logoutButton: {
        backgroundColor: '#c91414', // Red logout button
        color: '#fff',
        border: 'none',
        borderRadius: '10px',
        padding: '8px 12px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100px',
        height: '40px',
        transition: 'background-color 0.2s ease'
    },
    logoutButtonHover: {
        backgroundColor: '#d32f2f'
    },
    content: {
        flex: 1,                  // Ensures the content area expands
        overflowY: 'auto',        // Enables vertical scrolling
        padding: '5px',
        backgroundColor: '#f0f2f5' // Soft gray for background
    }
};