import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FaUserPlus } from 'react-icons/fa';
import { API_BASE_URL } from '../config';

const MIN_PASSWORD_LENGTH = 4;

export default function RegisterForm() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [email, setEmail] = useState('');
    const [registrationCode, setRegistrationCode] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [confirmError, setConfirmError] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        const pwError = password.length < MIN_PASSWORD_LENGTH
            ? `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
            : '';
        const cfError = password !== confirmPassword ? 'Passwords do not match.' : '';
        setPasswordError(pwError);
        setConfirmError(cfError);
        if (pwError || cfError) return;

        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/register`, {
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
                alert(data.message || 'Registration successful! Please check your email to verify your account.');
                navigate('/login');
            } else {
                setError(data.error || 'Registration failed');
            }
        } catch (err) {
            setError('Unable to connect to the server.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-brand">
                    <div className="auth-logo"><FaUserPlus /></div>
                    <h1>Create account</h1>
                    <p>You'll need a registration code from the owner</p>
                </div>

                <form onSubmit={handleRegister} className="form" noValidate>
                    {error && <div className="alert alert-error" role="alert">{error}</div>}

                    <div className="field">
                        <label htmlFor="reg-username">Username</label>
                        <input
                            id="reg-username"
                            type="text"
                            autoComplete="username"
                            autoCapitalize="none"
                            autoCorrect="off"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="reg-password">Password</label>
                        <input
                            id="reg-password"
                            type="password"
                            autoComplete="new-password"
                            className={passwordError ? 'invalid' : ''}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        {passwordError && <span className="field-error">{passwordError}</span>}
                    </div>

                    <div className="field">
                        <label htmlFor="reg-confirm">Confirm password</label>
                        <input
                            id="reg-confirm"
                            type="password"
                            autoComplete="new-password"
                            className={confirmError ? 'invalid' : ''}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                        {confirmError && <span className="field-error">{confirmError}</span>}
                    </div>

                    <div className="field">
                        <label htmlFor="reg-email">E-mail</label>
                        <input
                            id="reg-email"
                            type="email"
                            inputMode="email"
                            autoComplete="email"
                            autoCapitalize="none"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="reg-code">Registration code</label>
                        <input
                            id="reg-code"
                            type="text"
                            autoCapitalize="none"
                            autoCorrect="off"
                            value={registrationCode}
                            onChange={(e) => setRegistrationCode(e.target.value)}
                        />
                    </div>

                    <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                        {loading ? 'Creating account…' : 'Create account'}
                    </button>
                </form>

                <div className="auth-footer">
                    Already have an account? <Link to="/login" className="btn-link">Sign in</Link>
                </div>
            </div>
        </div>
    );
}
