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

const CategoryCard = ({ icon, title, description, onClick, large = false }) => {
  return (
    <div 
      className={`category-card ${large ? 'large' : ''}`}
      onClick={onClick}
    >
      <div className="category-icon">{icon}</div>
      <h3 className="category-title">{title}</h3>
      <p className="category-description">{description}</p>
    </div>
  );
};

function App() {
  const [currentView, setCurrentView] = useState('home'); // 'home', 'chat', 'explore'
  const [messages, setMessages] = useState([]);
  const [citedVerses, setCitedVerses] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [showVerses, setShowVerses] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  const [language, setLanguage] = useState('english');
  const [userName] = useState('Friend'); // Could be dynamic
  
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

  const startTapToChat = () => {
    setCurrentView('chat');
    setMessages([]);
    setCitedVerses([]);
  };

  const handleCategoryClick = (category) => {
    setCurrentView('chat');
    
    const categoryQuestions = {
      'Peace & Comfort': "How can I find peace and comfort in difficult times?",
      'Forgiveness': "What does the Bible teach about forgiveness?",
      'Faith & Trust': "How can I strengthen my faith and trust in God?",
      'Prayer': "How can I improve my prayer life?",
      'Purpose': "What is God's purpose for my life?",
      'Relationships': "What does the Bible say about relationships and love?",
      'Anxiety': "How can I overcome anxiety and worry through faith?",
      'Wisdom': "How can I gain biblical wisdom for decisions?"
    };
    
    const question = categoryQuestions[category] || `Tell me about ${category} from a biblical perspective.`;
    sendMessage(question);
  };

  const backToHome = () => {
    setCurrentView('home');
    setShowVerses(false);
  };

  // Home View
  if (currentView === 'home') {
    return (
      <div className={`app ${isDarkTheme ? 'dark-theme' : 'light-theme'}`}>
        {/* Header */}
        <header className="app-header">
          <div className="header-content">
            <div className="user-greeting">
              <div className="user-avatar">🙏</div>
              <div className="invite-section">
                <button className="invite-btn">+ Invite</button>
                <button className="menu-btn">☰</button>
              </div>
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
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="main-content">
          {/* Greeting */}
          <div className="greeting-section">
            <h1>Hi, {userName} 👋</h1>
          </div>

          {/* Tap to Chat Section */}
          <div className="tap-chat-section" onClick={startTapToChat}>
            <div className="chat-circle">
              <div className="audio-waves">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
            <h2>Tap to chat</h2>
            <p>Get biblical guidance and wisdom</p>
          </div>

          {/* Explore Section */}
          <div className="explore-section">
            <div className="section-header">
              <h2>Explore</h2>
              <button 
                className="explore-all-btn"
                onClick={() => setCurrentView('explore')}
              >
                View All
              </button>
            </div>
            
            <div className="categories-grid-home">
              <CategoryCard
                icon="☮️"
                title="Peace & Comfort"
                description="Find peace in difficult times through Scripture"
                onClick={() => handleCategoryClick('Peace & Comfort')}
              />
              <CategoryCard
                icon="💝"
                title="Forgiveness"
                description="Learn about God's forgiveness and grace"
                onClick={() => handleCategoryClick('Forgiveness')}
              />
            </div>
          </div>

          {/* Bottom Navigation */}
          <nav className="bottom-nav">
            <button className="nav-item active">
              <span className="nav-icon">⚪</span>
            </button>
            <button className="nav-item">
              <span className="nav-icon">🎤</span>
            </button>
            <button className="nav-item">
              <span className="nav-icon">👁️</span>
            </button>
            <button className="nav-item">
              <span className="nav-icon">🎯</span>
            </button>
          </nav>
        </main>
      </div>
    );
  }

  // Explore View
  if (currentView === 'explore') {
    return (
      <div className={`app ${isDarkTheme ? 'dark-theme' : 'light-theme'}`}>
        {/* Header */}
        <header className="app-header">
          <div className="header-content">
            <button className="back-btn" onClick={backToHome}>←</button>
            <h1>Explore</h1>
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
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="main-content">
          <div className="categories-grid-full">
            <CategoryCard
              icon="☮️"
              title="Peace & Comfort"
              description="Find peace in difficult times through biblical wisdom"
              onClick={() => handleCategoryClick('Peace & Comfort')}
            />
            <CategoryCard
              icon="💝"
              title="Forgiveness"
              description="Learn about God's forgiveness and how to forgive others"
              onClick={() => handleCategoryClick('Forgiveness')}
            />
            <CategoryCard
              icon="🛡️"
              title="Faith & Trust"
              description="Strengthen your faith and trust in God's plan"
              onClick={() => handleCategoryClick('Faith & Trust')}
            />
            <CategoryCard
              icon="🙏"
              title="Prayer"
              description="Improve your prayer life with biblical guidance"
              onClick={() => handleCategoryClick('Prayer')}
            />
            <CategoryCard
              icon="🎯"
              title="Purpose"
              description="Discover God's purpose and calling for your life"
              onClick={() => handleCategoryClick('Purpose')}
            />
            <CategoryCard
              icon="💕"
              title="Relationships"
              description="Biblical wisdom for relationships and love"
              onClick={() => handleCategoryClick('Relationships')}
            />
            <CategoryCard
              icon="🌅"
              title="Anxiety"
              description="Overcome anxiety and worry through faith"
              onClick={() => handleCategoryClick('Anxiety')}
            />
            <CategoryCard
              icon="🦉"
              title="Wisdom"
              description="Gain biblical wisdom for life's decisions"
              onClick={() => handleCategoryClick('Wisdom')}
            />
          </div>

          {/* Bottom Navigation */}
          <nav className="bottom-nav">
            <button className="nav-item">
              <span className="nav-icon">⚪</span>
            </button>
            <button className="nav-item">
              <span className="nav-icon">🎤</span>
            </button>
            <button className="nav-item active">
              <span className="nav-icon">👁️</span>
            </button>
            <button className="nav-item">
              <span className="nav-icon">🎯</span>
            </button>
          </nav>
        </main>
      </div>
    );
  }

  // Chat View
  return (
    <div className={`app ${isDarkTheme ? 'dark-theme' : 'light-theme'}`}>
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <button className="back-btn" onClick={backToHome}>←</button>
          <div className="chat-header-info">
            <h1>Preacher.ai</h1>
            <span className="subtitle">Biblical Guidance</span>
          </div>
          <div className="header-controls">
            {citedVerses.length > 0 && (
              <button 
                className={`verses-toggle ${showVerses ? 'active' : ''}`}
                onClick={() => setShowVerses(!showVerses)}
                title="Toggle Verses Panel"
              >
                📖 {citedVerses.length}
              </button>
            )}
            <button 
                className="theme-toggle"
                onClick={toggleTheme}
                title="Toggle Theme"
              >
                {isDarkTheme ? '☀️' : '🌙'}
              </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="chat-main-content">
        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="messages-container">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg.message}
                isUser={msg.sender === 'user'}
                citedVerses={msg.citedVerses}
              />
            ))}
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