import './App.css';
import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import Dashboard from './components/Dashboard';

function App() {
    const [isLoggedIn, setIsLoggedIn] = useState(() => localStorage.getItem('isLoggedIn') === 'true');
    const login = <LoginForm onLoginSuccess={() => setIsLoggedIn(true)} />;

    return (
        <Router>
            <Routes>
                <Route path="/" element={isLoggedIn ? <Navigate to="/dashboard" replace /> : login} />
                <Route path="/login" element={login} />
                <Route path="/register" element={<RegisterForm />} />
                <Route path="/dashboard" element={isLoggedIn ? <Dashboard /> : login} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </Router>
    );
}

export default App;
