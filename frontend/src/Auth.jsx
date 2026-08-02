import React, { useState } from 'react';
import './Auth.css';

const API_BASE_URL = "https://youtube-rag-chatbot-qirb.onrender.com";

function Auth({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [alertMsg, setAlertMsg] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAlertMsg({ type: '', text: '' });
    setLoading(true);

    const endpoint = isLogin ? '/auth/login' : '/auth/register';
    const payload = isLogin ? { email, password } : { username, email, password };

    try {
      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        if (isLogin) {
          localStorage.setItem('token', data.token);
          localStorage.setItem('username', data.username);
          onAuthSuccess(data.username, data.token);
        } else {
          setIsLogin(true);
          setAlertMsg({ type: 'info', text: 'Account created! Log in below.' });
          setPassword('');
        }
      } else {
        setAlertMsg({ type: 'error', text: data.error || 'Authentication failed.' });
      }
    } catch (err) {
      setAlertMsg({ type: 'error', text: 'Unable to connect to server.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      {/* Blurred Mosaic Cards Background */}
      <div className="auth-bg-grid">
        {[...Array(15)].map((_, i) => (
          <div key={i} className="bg-card"></div>
        ))}
      </div>

      {}
      <div className="auth-card">
        <div className="auth-brand-logo">🎬</div>
        
        <h2>{isLogin ? 'Ask anything.\nFree on RAG AI.' : 'Sign up to start\nasking questions.'}</h2>
        <p className="auth-subtitle">Chat with any YouTube video in seconds.</p>

        {alertMsg.text && (
          <div className={`auth-alert ${alertMsg.type}`}>
            {alertMsg.text}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="input-group">
              <label>What should we call you?</label>
              <div className="input-wrapper">
                <input 
                  type="text" 
                  required 
                  value={username} 
                  onChange={(e) => setUsername(e.target.value)} 
                  placeholder="Enter a profile name"
                />
              </div>
            </div>
          )}

          <div className="input-group">
            <label>What's your email?</label>
            <div className="input-wrapper">
              <input 
                type="email" 
                required 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                placeholder="name@domain.com"
              />
            </div>
          </div>

          <div className="input-group">
            <label>Create a password</label>
            <div className="input-wrapper">
              <input 
                type="password" 
                required 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                placeholder="••••••••"
              />
            </div>
          </div>

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Processing...' : (isLogin ? 'Log In' : 'Sign Up Free')}
          </button>
        </form>

        <div className="auth-divider"></div>

        <p className="toggle-auth">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <span onClick={() => { setIsLogin(!isLogin); setAlertMsg({ type: '', text: '' }); }}>
            {isLogin ? 'Sign up free' : 'Log in'}
          </span>
        </p>
      </div>
    </div>
  );
}

export default Auth;