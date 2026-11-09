import React, { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaSignOutAlt, FaVideo } from 'react-icons/fa';
import LiveStream from './LiveStream';
import ToggleMode from './ToggleMode';
import ClipsList from './ClipsList';
import { API_BASE_URL } from '../config';

export default function Dashboard() {
    const navigate = useNavigate();
    const [isArmed, setIsArmed] = useState(null); // null = not loaded yet
    const [toast, setToast] = useState(null);
    const toastTimer = useRef(null);
    const username = localStorage.getItem('username');

    const notify = useCallback((message, type = 'info') => {
        clearTimeout(toastTimer.current);
        setToast({ message, type });
        toastTimer.current = setTimeout(() => setToast(null), 3000);
    }, []);

    const handleLogout = async () => {
        try {
            await fetch(`${API_BASE_URL}/api/logout`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (err) {
            console.error('Logout error:', err);
        }
        // Clear local state regardless, so the user is never stuck logged in
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('username');
        navigate('/login');
    };

    return (
        <>
            <header className="app-header">
                <div className="app-title">
                    <FaVideo className="logo" />
                    <h1>Surveillance</h1>
                    {isArmed !== null && (
                        <span className={`pill ${isArmed ? 'pill-armed' : 'pill-disarmed'}`}>
                            <span className="dot" />
                            {isArmed ? 'Armed' : 'Disarmed'}
                        </span>
                    )}
                </div>
                <div className="header-actions">
                    {username && <span className="header-user">{username}</span>}
                    <button
                        className="icon-btn danger"
                        onClick={handleLogout}
                        title="Sign out"
                        aria-label="Sign out"
                    >
                        <FaSignOutAlt size={18} />
                    </button>
                </div>
            </header>

            <main className="dashboard">
                <div className="dashboard-main">
                    <LiveStream />
                    <ToggleMode onArmedChange={setIsArmed} notify={notify} />
                </div>
                <div className="dashboard-side">
                    <ClipsList notify={notify} />
                </div>
            </main>

            {toast && (
                <div className={`toast ${toast.type === 'error' ? 'error' : ''}`} role="status">
                    {toast.message}
                </div>
            )}
        </>
    );
}
