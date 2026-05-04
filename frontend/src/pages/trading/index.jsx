import React, { useState, useEffect } from 'react';
import PasswordGate from './components/PasswordGate';
import TradingTerminal from './components/TradingTerminal';
import { BindingProvider } from '../../components/terminal/binding/BindingProvider';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const TradingPage = () => {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if already authenticated (dev mode bypass)
    const isDevMode = process.env.NODE_ENV === 'development';
    const storedAuth = sessionStorage.getItem('terminal_auth');
    
    if (storedAuth === 'true' || isDevMode) {
      setAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleAuthenticate = async (password) => {
    try {
      const response = await fetch(`${API_URL}/api/terminal/auth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      const data = await response.json();
      
      if (data.ok && data.authenticated) {
        sessionStorage.setItem('terminal_auth', 'true');
        setAuthenticated(true);
        return { success: true };
      }
      return { success: false, message: data.message || 'Invalid password' };
    } catch (error) {
      console.error('Auth error:', error);
      return { success: false, message: 'Connection error' };
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-700 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  if (!authenticated) {
    return <PasswordGate onAuthenticate={handleAuthenticate} />;
  }

  return (
    <BindingProvider>
      <TradingTerminal />
    </BindingProvider>
  );
};

export default TradingPage;
