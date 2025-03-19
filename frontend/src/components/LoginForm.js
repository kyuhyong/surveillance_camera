import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function LoginForm({ onLoginSuccess }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    // Login Handler
    const handleLogin = async (e) => {
        e.preventDefault();  // Prevents page reload

        try {
            const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                //alert('Login successful!');
                localStorage.setItem('isLoggedIn', 'true');  // Store session in localStorage
                localStorage.setItem('username', username);  // Store username
                onLoginSuccess();  // Update parent state
                navigate('/dashboard');  // 👈 Redirect to dashboard or main screen
            } else {
                alert(`Login failed: ${data.error}`);
            }
        } catch (error) {
            alert('Network error: Unable to connect to server.');
        }
    };
    const handleRegister = () => {
        navigate('/register');  // Redirect to the registration page
    };

    return (
        <div style={styles.container}>
            <h2>Login</h2>

            {/* Form with onSubmit for Enter key support */}
            <form onSubmit={handleLogin} style={styles.form}>
                <div style={styles.inputGroup}>
                    <label>Username:</label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                    />
                </div>

                <div style={styles.inputGroup}>
                    <label>Password:</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                </div>
                {/* Login Button */}
                <button type="submit" style={styles.button}> {/* onClick={handleLogin}>*/}
                    Login
                </button>
                {/* Registration Button Added */}
                <p>Don't have an account?</p>
                <button type="submit" onClick={handleRegister}>Register</button>
                
            </form>
        </div>
    );
}
const styles = {
    container: {
        width: '300px',
        margin: '100px auto',
        padding: '20px',
        border: '2px solid #4CAF50',
        borderRadius: '8px',
        backgroundColor: '#f0f2f5'
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '15px'
    },
    inputGroup: {
        display: 'flex',
        flexDirection: 'column'
    },
    button: {
        backgroundColor: '#4CAF50',
        color: '#fff',
        border: 'none',
        padding: '10px',
        borderRadius: '5px',
        cursor: 'pointer',
        transition: 'background-color 0.2s ease'
    },
    buttonHover: {
        backgroundColor: '#45a049'
    }
};