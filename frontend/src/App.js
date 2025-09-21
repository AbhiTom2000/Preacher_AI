import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ChatMessage = ({ message, isUser, citedVerses = [] }) => {
  return (
    <div className={`message-container ${isUser ? 'user-message' : 'ai-message'}`}>
      <div className="message-bubble">
        <div className="message-content">
          {message}
        </div>
        {!isUser && citedVerses.length > 0 && (
          <div className="cited-indicator">
            <span>📖 {citedVerses.length} verse{citedVerses.length > 1 ? 's' : ''} cited</span>
          </div>
        )}
      </div>
    </div>
  );
};

const VerseCard = ({ verse }) => {
  return (
    <div className="verse-card">
      <div className="verse-reference">{verse.reference}</div>
      <div className="verse-text">"{verse.text}"</div>
    </div>
  );
};

const LoadingSkeleton = () => {
  return (
    <div className="message-container ai-message">
      <div className="message-bubble loading">
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div className="loading-text">Preacher.ai is thinking...</div>
      </div>
    </div>
  );
};

const QuickStarters = ({ onQuestionSelect }) => {
  const questions = [
    "How can I find peace in difficult times?",
    "What does the Bible say about forgiveness?",
    "Help me with anxiety and worry",
    "How to strengthen my faith?",
    "What is God's purpose for my life?",
    "How to pray effectively?"
  ];

  return (
    <div className="quick-starters">
      <h3>Ask Preacher.ai</h3>
      <div className="starter-questions">
        {questions.map((question, index) => (
          <button
            key={index}
            className="starter-question"
            onClick={() => onQuestionSelect(question)}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState([]);
  const [citedVerses, setCitedVerses] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [showVerses, setShowVerses] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  const [language, setLanguage] = useState('english');
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    createSession();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const createSession = async () => {
    try {
      const response = await axios.post(`${API}/session`);
      setSessionId(response.data.session_id);
    } catch (error) {
      console.error('Error creating session:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async (message = inputMessage) => {
    if (!message.trim() || !sessionId) return;

    const userMessage = {
      id: Date.now(),
      message: message,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat`, {
        message: message,
        session_id: sessionId
      });

      const aiMessage = {
        id: Date.now() + 1,
        message: response.data.response,
        sender: 'ai',
        timestamp: new Date(),
        citedVerses: response.data.cited_verses || []
      };

      setMessages(prev => [...prev, aiMessage]);
      
      if (response.data.cited_verses && response.data.cited_verses.length > 0) {
        setCitedVerses(response.data.cited_verses);
        setShowVerses(true);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        message: 'I apologize, but I\'m having trouble connecting right now. Please try again in a moment.',
        sender: 'ai',
        timestamp: new Date(),
        citedVerses: []
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleTheme = () => {
    setIsDarkTheme(!isDarkTheme);
  };

  const toggleLanguage = () => {
    setLanguage(language === 'english' ? 'hindi' : 'english');
  };

  return (
    <div className={`app ${isDarkTheme ? 'dark-theme' : 'light-theme'}`}>
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo">🙏</div>
            <h1>Preacher.ai</h1>
            <span className="subtitle">AI-Powered Biblical Guidance</span>
          </div>
          <div className="header-controls">
            <button 
              className="language-toggle"
              onClick={toggleLanguage}
              title="Switch Language"
            >
              {language === 'english' ? 'हिं' : 'EN'}
            </button>
            <button 
              className="theme-toggle"
              onClick={toggleTheme}
              title="Toggle Theme"
            >
              {isDarkTheme ? '☀️' : '🌙'}
            </button>
            {citedVerses.length > 0 && (
              <button 
                className={`verses-toggle ${showVerses ? 'active' : ''}`}
                onClick={() => setShowVerses(!showVerses)}
                title="Toggle Verses Panel"
              >
                📖 {citedVerses.length}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="messages-container">
            {messages.length === 0 ? (
              <QuickStarters onQuestionSelect={sendMessage} />
            ) : (
              messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg.message}
                  isUser={msg.sender === 'user'}
                  citedVerses={msg.citedVerses}
                />
              ))
            )}
            {isLoading && <LoadingSkeleton />}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form className="input-container" onSubmit={handleSubmit}>
            <div className="input-wrapper">
              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={language === 'english' 
                  ? "Ask for biblical guidance..." 
                  : "बाइबल मार्गदर्शन के लिए पूछें..."
                }
                disabled={isLoading}
                rows="1"
              />
              <button 
                type="submit" 
                className="send-button"
                disabled={!inputMessage.trim() || isLoading}
              >
                {isLoading ? '⏳' : '➤'}
              </button>
            </div>
          </form>
        </div>

        {/* Verses Panel */}
        <div className={`verses-panel ${showVerses ? 'visible' : ''}`}>
          <div className="verses-header">
            <h3>📖 Cited Scripture</h3>
            <button 
              className="close-verses"
              onClick={() => setShowVerses(false)}
            >
              ✕
            </button>
          </div>
          <div className="verses-content">
            {citedVerses.map((verse, index) => (
              <VerseCard key={index} verse={verse} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;