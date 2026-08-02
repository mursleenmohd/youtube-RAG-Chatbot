import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import Auth from './Auth';
import './App.css';

const API_BASE_URL = "http://localhost:5000/api";

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [username, setUsername] = useState(localStorage.getItem('username') || '');

  const [videoUrl, setVideoUrl] = useState('');
  const [activeEmbedId, setActiveEmbedId] = useState('');
  const [seekSeconds, setSeekSeconds] = useState(0);
  const [isProcessed, setIsProcessed] = useState(false);
  const [loadingVideo, setLoadingVideo] = useState(false);

  const [savedVideos, setSavedVideos] = useState([]);
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loadingChat, setLoadingChat] = useState(false);

  const [statusMessage, setStatusMessage] = useState({ type: '', text: '' });
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (token) fetchSavedVideos();
  }, [token]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, loadingChat]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setToken('');
    setUsername('');
    setChatHistory([]);
    setSavedVideos([]);
    setActiveEmbedId('');
  };

  const getAuthHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  });

  const extractVideoId = (url) => {
    if (url.includes("watch?v=")) return url.split("watch?v=")[1]?.split("&")[0];
    if (url.includes("youtu.be/")) return url.split("youtu.be/")[1]?.split("?")[0];
    return null;
  };

  const timestampToSeconds = (timestampStr) => {
    const parts = timestampStr.replace('[', '').replace(']', '').split(':');
    return parts.length === 2 ? parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10) : 0;
  };

  const fetchSavedVideos = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/videos`, { headers: getAuthHeaders() });
      const data = await res.json();
      if (res.ok) setSavedVideos(data.videos || []);
    } catch (err) {
      console.error("Failed to load saved videos", err);
    }
  };

  const fetchChatHistory = async (vId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/history/${vId}`, { headers: getAuthHeaders() });
      const data = await res.json();
      if (res.ok) setChatHistory(data.history || []);
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const handleSelectSavedVideo = async (vid) => {
    const fullUrl = `https://www.youtube.com/watch?v=${vid.video_id}`;
    setVideoUrl(fullUrl);
    setActiveEmbedId(vid.video_id);
    setSeekSeconds(0);
    setIsProcessed(true);

    await fetchChatHistory(vid.video_id);
    fetch(`${API_BASE_URL}/process-video`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ video_url: fullUrl })
    });
  };

  const handleProcessVideo = async () => {
    const vId = extractVideoId(videoUrl);
    if (!vId) return setStatusMessage({ type: 'error', text: 'Invalid URL' });

    setLoadingVideo(true);
    try {
      const res = await fetch(`${API_BASE_URL}/process-video`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ video_url: videoUrl })
      });
      const data = await res.json();

      if (res.ok) {
        setIsProcessed(true);
        setActiveEmbedId(vId);
        setStatusMessage({ type: 'success', text: 'Indexed successfully!' });
        await fetchChatHistory(vId);
        await fetchSavedVideos();
      } else {
        setStatusMessage({ type: 'error', text: data.error });
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: 'Server error' });
    } finally {
      setLoadingVideo(false);
    }
  };

  const handleSendQuestion = async () => {
    if (!question.trim() || !isProcessed || !activeEmbedId) return;

    const currentQ = question;
    setQuestion('');
    setChatHistory(prev => [...prev, { sender: 'user', text: currentQ }, { sender: 'bot', text: '' }]);
    setLoadingChat(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat-stream`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ question: currentQ, video_id: activeEmbedId })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });

        setChatHistory(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { sender: 'bot', text: accumulated };
          return updated;
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingChat(false);
    }
  };

  const renderFormattedMessage = (text) => {
    const timestampRegex = /(\[\d{2}:\d{2}\])/g;
    const parts = text.split(timestampRegex);

    return parts.map((part, i) => {
      if (timestampRegex.test(part)) {
        return (
          <button 
            key={i} 
            className="timestamp-btn"
            onClick={() => setSeekSeconds(timestampToSeconds(part))}
          >
            ⏱️ {part}
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  if (!token) {
    return <Auth onAuthSuccess={(user, tok) => { setUsername(user); setToken(tok); }} />;
  }

  return (
    <div>
      <header className="app-header">
        <h1>🎬 YouTube Interactive RAG Chatbot</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>👤 {username}</span>
          <button onClick={handleLogout} style={{ background: '#dc2626', padding: '6px 12px', fontSize: '0.8rem' }}>
            Logout
          </button>
        </div>
      </header>

      <div className="main-layout">
        {/* Sidebar */}
        <div className="sidebar">
          <div className="sidebar-header">
            <span>Your Sessions ({savedVideos.length})</span>
          </div>
          <div className="video-list">
            {savedVideos.map((vid) => (
              <div 
                key={vid.id} 
                className={`video-item ${activeEmbedId === vid.video_id ? 'active' : ''}`}
                onClick={() => handleSelectSavedVideo(vid)}
              >
                <span className="video-item-title">📹 {vid.video_id}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Video Player */}
        <div className="video-panel">
          <div className="url-box">
            <input 
              type="text" 
              placeholder="Paste YouTube Video Link..." 
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
            />
            <button onClick={handleProcessVideo} disabled={loadingVideo}>
              {loadingVideo ? 'Indexing...' : 'Index Video'}
            </button>
          </div>

          {statusMessage.text && (
            <div className={`status-msg ${statusMessage.type}`}>{statusMessage.text}</div>
          )}

          <div className="player-wrapper">
            {activeEmbedId ? (
              <iframe
                width="100%"
                height="100%"
                src={`https://www.youtube.com/embed/${activeEmbedId}?autoplay=1&start=${seekSeconds}`}
                title="YouTube player"
                frameBorder="0"
                allowFullScreen
              ></iframe>
            ) : (
              <div className="player-placeholder">Paste video link or select session</div>
            )}
          </div>
        </div>

        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="chat-box">
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`message ${msg.sender}`}>
                {msg.sender === 'bot' ? renderFormattedMessage(msg.text) : msg.text}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-input-area">
            <input 
              type="text" 
              placeholder={isProcessed ? "Ask about video..." : "Index video first..."} 
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendQuestion()}
              disabled={!isProcessed || loadingChat}
            />
            <button onClick={handleSendQuestion} disabled={!isProcessed || loadingChat}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;