import './App.css';
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import Dashboard from './components/Dashboard';

function App() {
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    useEffect(() => {
        // Check session in localStorage
        const isLoggedInStored = localStorage.getItem('isLoggedIn');
        if (isLoggedInStored === 'true') {
            setIsLoggedIn(true);
        } else {
            setIsLoggedIn(false);
        }
    }, []);

    return (
        <Router>
            <Routes>
                <Route path="/login" element={<LoginForm onLoginSuccess={() => setIsLoggedIn(true)} />} />
                <Route path="/register" element={<RegisterForm />} />
                <Route
                    path="/dashboard"
                    element={isLoggedIn ? <Dashboard /> : <LoginForm onLoginSuccess={() => setIsLoggedIn(true)} />}
                />
                <Route path="*" element={<LoginForm onLoginSuccess={() => setIsLoggedIn(true)} />} />
            </Routes>
        </Router>
    );
}

export default App;
