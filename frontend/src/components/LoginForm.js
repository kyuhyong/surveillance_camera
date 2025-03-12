import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function LoginForm({ onLoginSuccess }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    const handleLogin = async () => {
        try {
            const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                alert('Login successful!');
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
        <div>
            <h2>Login</h2>
            <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
            />
            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
            />
            <button onClick={handleLogin}>Login</button>
            {/* Registration Button Added */}
            <p>Don't have an account?</p>
            <button onClick={handleRegister}>Register</button>
        </div>
    );
}
