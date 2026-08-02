import React, { useState } from 'react';
import './Auth.css';

const API_BASE_URL = "https://youtube-rag-chatbot-qirb.onrender.com";

function Auth({ onAuthSuccess }) {
  // Modes: 'login' | 'signup' | 'forgot'
  const [mode, setMode] = useState('login');
  
  // For 'forgot' mode: Step 1 = Send OTP, Step 2 = Verify OTP & Set New Password
  const [step, setStep] = useState(1);

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  
  const [alertMsg, setAlertMsg] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAlertMsg({ type: '', text: '' });
    setLoading(true);

    // -----------------------------------------------------------
    // 1. FORGOT PASSWORD FLOW
    // -----------------------------------------------------------
    if (mode === 'forgot') {
      if (step === 1) {
        // Step 1: Request OTP
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
          });
          const data = await res.json();
          
          if (res.ok) {
            setAlertMsg({ type: 'info', text: 'OTP sent! Check your email inbox.' });
            setStep(2);
          } else {
            setAlertMsg({ type: 'error', text: data.error || 'Failed to send OTP.' });
          }
        } catch (err) {
          setAlertMsg({ type: 'error', text: 'Unable to connect to server.' });
        }
      } else {
        // Step 2: Reset Password with OTP
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp, password })
          });
          const data = await res.json();

          if (res.ok) {
            setAlertMsg({ type: 'info', text: 'Password reset successful! Please log in.' });
            setMode('login');
            setStep(1);
            setPassword('');
            setOtp('');
          } else {
            setAlertMsg({ type: 'error', text: data.error || 'Invalid OTP or Reset failed.' });
          }
        } catch (err) {
          setAlertMsg({ type: 'error', text: 'Unable to connect to server.' });
        }
      }
      setLoading(false);
      return;
    }

    // -----------------------------------------------------------
    // 2. STANDARD LOGIN / SIGNUP FLOW
    // -----------------------------------------------------------
    const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
    const payload = mode === 'login' ? { email, password } : { username, email, password };

    try {
      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        if (mode === 'login') {
          localStorage.setItem('token', data.token);
          localStorage.setItem('username', data.username);
          onAuthSuccess(data.username, data.token);
        } else {
          setMode('login');
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
      {/* Background Cards Grid */}
      <div className="auth-bg-grid">
        {[...Array(15)].map((_, i) => (
          <div key={i} className="bg-card"></div>
        ))}
      </div>

      <div className="auth-card">
        <div className="auth-brand-logo">🎬</div>
        
        <h2>
          {mode === 'login' && 'Ask anything.\nFree on RAG AI.'}
          {mode === 'signup' && 'Sign up to start\nasking questions.'}
          {mode === 'forgot' && 'Reset Your\nPassword.'}
        </h2>
        
        <p className="auth-subtitle">
          {mode === 'forgot' 
            ? (step === 1 ? 'Enter email to receive 6-digit OTP' : 'Enter OTP code & new password') 
            : 'Chat with any YouTube video in seconds.'}
        </p>

        {alertMsg.text && (
          <div className={`auth-alert ${alertMsg.type}`}>
            {alertMsg.text}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {/* Signup Username Field */}
          {mode === 'signup' && (
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

          {/* Email Field (Hidden in step 2 of forgot mode) */}
          {(mode !== 'forgot' || step === 1) && (
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
          )}

          {/* Forgot Password Step 2: OTP & New Password */}
          {mode === 'forgot' && step === 2 && (
            <>
              <div className="input-group">
                <label>Enter 6-Digit OTP Code</label>
                <div className="input-wrapper">
                  <input 
                    type="text" 
                    required 
                    maxLength="6"
                    value={otp} 
                    onChange={(e) => setOtp(e.target.value)} 
                    placeholder="123456"
                  />
                </div>
              </div>

              <div className="input-group">
                <label>Create New Password</label>
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
            </>
          )}

          {/* Password Field for Login & Signup */}
          {mode !== 'forgot' && (
            <div className="input-group">
              <div className="label-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label>Password</label>
                {mode === 'login' && (
                  <span 
                    className="forgot-link" 
                    style={{ fontSize: '12px', color: '#38bdf8', cursor: 'pointer' }}
                    onClick={() => { setMode('forgot'); setStep(1); setAlertMsg({ type: '', text: '' }); }}
                  >
                    Forgot password?
                  </span>
                )}
              </div>
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
          )}

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Processing...' : (
              mode === 'login' ? 'Log In' : 
              mode === 'signup' ? 'Sign Up Free' : 
              step === 1 ? 'Send Verification OTP' : 'Update Password'
            )}
          </button>
        </form>

        <div className="auth-divider"></div>

        <p className="toggle-auth">
          {mode === 'login' && "Don't have an account?"}
          {mode === 'signup' && "Already have an account?"}
          {mode === 'forgot' && "Remembered your password?"}
          
          <span onClick={() => { 
            setMode(mode === 'login' ? 'signup' : 'login'); 
            setStep(1);
            setAlertMsg({ type: '', text: '' }); 
          }}>
            {mode === 'login' ? ' Sign up free' : ' Log in'}
          </span>
        </p>
      </div>
    </div>
  );
}

export default Auth;