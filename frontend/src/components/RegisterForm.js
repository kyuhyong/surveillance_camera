import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function RegisterForm() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [email, setEmail] = useState('');
    const [registrationCode, setRegistrationCode] = useState('');
    const navigate = useNavigate();

    const handleRegister = async () => {
        try {
            const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    password,
                    email,
                    registration_code: registrationCode
                })
            });

            const data = await response.json();
            if (response.ok) {
                alert('Registration successful! Please check your email to verify your account.');
                navigate('/login');
            } else {
                alert(`Registration failed: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            alert('Network error: Unable to connect to server.');
        }
    };

    return (
        <div>
            <h2>Register</h2>
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
            <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
            />
            <input
                type="text"
                placeholder="Registration Code"
                value={registrationCode}
                onChange={(e) => setRegistrationCode(e.target.value)}
            />
            <button onClick={handleRegister}>Register</button>
        </div>
    );
}
