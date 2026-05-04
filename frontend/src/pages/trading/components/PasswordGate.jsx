import React, { useState } from 'react';
import { Lock, AlertCircle } from 'lucide-react';

const PasswordGate = ({ onAuthenticate }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password.length < 4) {
      setError('Password too short');
      return;
    }
    
    setLoading(true);
    setError('');
    
    const result = await onAuthenticate(password);
    
    if (!result.success) {
      setError(result.message || 'Access denied');
      setLoading(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/95 backdrop-blur-md"
      data-testid="password-gate"
    >
      <div className="bg-gray-900 p-8 border border-gray-700 rounded-sm shadow-2xl max-w-sm w-full flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center">
            <Lock className="w-8 h-8 text-gray-400" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold text-white tracking-tight uppercase">
              Trading Terminal
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Enter access code to continue
            </p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="****"
              className="w-full border-b border-gray-600 bg-transparent focus:border-white px-0 py-3 outline-none text-3xl tracking-[0.5em] text-center transition-colors font-mono text-white placeholder:text-gray-700"
              data-testid="password-input"
              autoFocus
              disabled={loading}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm justify-center">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || password.length < 4}
            className="w-full py-3 bg-white text-gray-900 font-bold uppercase tracking-widest text-sm hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="submit-button"
          >
            {loading ? 'Verifying...' : 'Enter Terminal'}
          </button>
        </form>

        {/* Dev hint */}
        {process.env.NODE_ENV === 'development' && (
          <p className="text-xs text-gray-600 text-center">
            Dev mode: any 4+ char password works
          </p>
        )}
      </div>
    </div>
  );
};

export default PasswordGate;
