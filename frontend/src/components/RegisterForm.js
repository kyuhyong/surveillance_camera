import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function RegisterForm() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [email, setEmail] = useState('');
    const [registrationCode, setRegistrationCode] = useState('');
    const [confirmError, setConfirmError] = useState('');
    const navigate = useNavigate();

    // Password Strength Check
    const validatePassword = (password) => {
        const minLength = password.length >= 4;
        // const hasUppercase = /[A-Z]/.test(password);
        // const hasLowercase = /[a-z]/.test(password);
        // const hasNumber = /\d/.test(password);
        // const hasSpecialChar = /[@$!%*?&]/.test(password);

        if (!minLength) return "Password must be at least 8 characters.";
        // if (!hasUppercase) return "Password must include an uppercase letter.";
        // if (!hasLowercase) return "Password must include a lowercase letter.";
        // if (!hasNumber) return "Password must include a number.";
        // if (!hasSpecialChar) return "Password must include a special character (@, $, !, %, etc.).";

        return "";  // Empty string means the password is valid
    };

    const handleRegister = async (e) => {
        e.preventDefault();

        // Validate password
        const passwordError = validatePassword(password);
        if (passwordError) {
            setPasswordError(passwordError);
            return;
        } else {
            setPasswordError('');
        }

        // Confirm Password Check
        if (password !== confirmPassword) {
            setConfirmError('Passwords do not match.');
            return;
        } else {
            setConfirmError('');
        }

        // Proceed with registration logic
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
        <div style={styles.container}>
            <h2>Register</h2>
            <form onSubmit={handleRegister} style={styles.form}>
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
                <div style={styles.inputGroup}>
                    <label>Confirm Password:</label>
                    <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                    />
                    {confirmError && <p style={styles.error}>{confirmError}</p>}
                </div>
                <div style={styles.inputGroup}>
                    <label>E-mail:</label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                </div>
                <div style={styles.inputGroup}>
                    <label>Registration Code:</label>
                    <input
                        type="text"
                        value={registrationCode}
                        onChange={(e) => setRegistrationCode(e.target.value)}
                    />
                </div>
                <button type="submit" style={styles.button}>
                    Register
                </button>
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
    error: {
        color: '#f44336',
        fontSize: '14px',
        marginTop: '5px'
    }
};