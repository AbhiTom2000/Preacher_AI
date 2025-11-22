import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Bot,
  BookOpen,
  Heart,
  MessageCircle,
  Sparkles,
  ArrowRight,
  Menu,
  X,
  Send,
  User,
  Info,
  Loader2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Import assets
import logoImg from './assets/logo.png';
import mountainBg from './assets/mountain-bg.png';

// Configuration
const WS_BASE = process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000/ws/chat';
const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'; // reserved for future REST calls

// Utility functions
const uuidv4 = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });

const SESSION_KEY = 'preacher_session_id';
function getOrCreateSessionId() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = uuidv4();
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

// Landing Page Component
function LandingPage({ onGetStarted }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-gray-950 to-black text-white overflow-x-hidden">
      {/* Navigation */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'bg-black/80 backdrop-blur-lg border-b border-white/10' : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="absolute inset-0 bg-white/20 rounded-lg blur opacity-50"></div>
                <div className="relative w-10 h-10 flex items-center justify-center">
                  <img src={logoImg} alt="Preacher AI" className="w-10 h-10 object-contain drop-shadow-lg" />
                </div>
              </div>
              <span className="text-xl font-bold text-white">Preacher AI</span>
            </div>

            <div className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-gray-300 hover:text-white transition-colors">
                Features
              </a>
              <a href="#about" className="text-gray-300 hover:text-white transition-colors">
                About
              </a>
              <button
                onClick={onGetStarted}
                className="bg-white hover:bg-gray-200 text-black px-6 py-2 rounded-full font-semibold transition-all duration-300 transform hover:scale-105 shadow-lg shadow-white/20"
              >
                Get Started
              </button>
            </div>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden text-gray-300 hover:text-white"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden bg-black/95 backdrop-blur-lg border-t border-white/10">
            <div className="px-4 py-6 space-y-4">
              <a href="#features" className="block text-gray-300 hover:text-white transition-colors">
                Features
              </a>
              <a href="#about" className="block text-gray-300 hover:text-white transition-colors">
                About
              </a>
              <button
                onClick={onGetStarted}
                className="w-full bg-white text-black px-6 py-2 rounded-full font-semibold"
              >
                Get Started
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
        {/* Background Image */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-b from-black/90 via-gray-950/70 to-black/95 z-10"></div>
          <img src={mountainBg} alt="Mountain Background" className="w-full h-full object-cover" />
        </div>

        {/* Animated Background Effects */}
        <div className="absolute inset-0 overflow-hidden z-20">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl animate-pulse"></div>
          <div
            className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl animate-pulse"
            style={{ animationDelay: '1s' }}
          ></div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center z-30">
          {/* Logo */}
          <div className="mb-8 flex justify-center animate-fadeIn">
            <div className="relative">
              <div className="absolute inset-0 bg-white/30 blur-3xl opacity-40 animate-pulse"></div>
              <div className="relative w-32 h-32 flex items-center justify-center">
                <img src={logoImg} alt="Preacher AI Logo" className="w-full h-full object-contain drop-shadow-2xl" />
              </div>
            </div>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold mb-6 animate-fadeInUp">
            <span className="text-white drop-shadow-lg">Preacher AI</span>
          </h1>

          <p
            className="text-xl sm:text-2xl text-gray-300 mb-4 max-w-3xl mx-auto animate-fadeInUp"
            style={{ animationDelay: '0.2s' }}
          >
            Your AI-Powered Pastoral Companion
          </p>

          <p
            className="text-lg text-gray-400 mb-12 max-w-2xl mx-auto animate-fadeInUp"
            style={{ animationDelay: '0.3s' }}
          >
            Experience biblical wisdom, sermon preparation, and spiritual guidance powered by advanced AI technology.
          </p>

          <div
            className="flex flex-col sm:flex-row gap-4 justify-center animate-fadeInUp"
            style={{ animationDelay: '0.4s' }}
          >
            <button
              onClick={onGetStarted}
              className="group relative px-8 py-4 bg-white hover:bg-gray-200 text-black rounded-full font-semibold text-lg overflow-hidden transition-all duration-300 transform hover:scale-105 shadow-2xl shadow-white/30"
            >
              <span className="relative z-10 flex items-center justify-center gap-2">
                Get Started
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
          </div>

          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
            <div className="w-6 h-10 border-2 border-gray-400 rounded-full flex items-start justify-center p-2">
              <div className="w-1 h-2 bg-gray-400 rounded-full"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold mb-4 text-white">Powerful Features</h2>
            <p className="text-xl text-gray-400">Everything you need for pastoral excellence</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: <BookOpen className="w-8 h-8" />,
                title: 'Biblical Insights',
                description: 'Access deep scriptural knowledge and verse citations for every conversation.'
              },
              {
                icon: <MessageCircle className="w-8 h-8" />,
                title: 'Sermon Preparation',
                description: 'Create compelling sermons with AI-assisted research and structure.'
              },
              {
                icon: <Heart className="w-8 h-8" />,
                title: 'Pastoral Guidance',
                description: 'Receive thoughtful counsel rooted in biblical wisdom.'
              },
              {
                icon: <Sparkles className="w-8 h-8" />,
                title: 'Scripture Search',
                description: 'Instantly find relevant verses for any topic or situation.'
              },
              {
                icon: <Bot className="w-8 h-8" />,
                title: 'AI-Powered',
                description: 'Leveraging cutting-edge AI for accurate and relevant responses.'
              },
              {
                icon: <BookOpen className="w-8 h-8" />,
                title: 'Study Tools',
                description: 'Comprehensive resources for deep biblical study and exploration.'
              }
            ].map((feature, index) => (
              <div
                key={index}
                className="group relative p-8 rounded-2xl bg-gradient-to-b from-gray-900/50 to-black/50 border border-white/10 hover:border-white/30 transition-all duration-300 hover:-translate-y-2"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 to-white/0 group-hover:from-white/5 group-hover:to-white/5 rounded-2xl transition-all duration-300"></div>
                <div className="relative">
                  <div className="mb-4 inline-block p-3 bg-white/10 rounded-xl text-white group-hover:text-white group-hover:bg-white/20 transition-colors">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-2 text-white">{feature.title}</h3>
                  <p className="text-gray-400">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-white/5 to-white/5"></div>
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="text-4xl sm:text-5xl font-bold mb-6 text-white">Ready to Get Biblified?</h2>
          <p className="text-xl text-gray-300 mb-8">Have your own pastor using Preacher AI.</p>
          <button
            onClick={onGetStarted}
            className="group relative px-10 py-5 bg-white hover:bg-gray-200 text-black rounded-full font-semibold text-lg overflow-hidden transition-all duration-300 transform hover:scale-105 shadow-2xl shadow-white/30"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              Start Your Journey
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </span>
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 flex items-center justify-center">
                <img src={logoImg} alt="Preacher AI" className="w-10 h-10 object-contain" />
              </div>
              <span className="text-xl font-bold text-white">Preacher AI</span>
            </div>
            <div className="text-gray-400 text-center md:text-left">
              <p>&copy; 2025 Preacher AI. Empowering Bible through technology.</p>
            </div>
          </div>
        </div>
      </footer>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-20px); } }
        .animate-fadeIn { animation: fadeIn 1s ease-out; }
        .animate-fadeInUp { animation: fadeInUp 1s ease-out; animation-fill-mode: both; }
        .animate-float { animation: float 6s ease-in-out infinite; }
      `}</style>
    </div>
  );
}

// Chat Interface Component
function ChatInterface({ onBack }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [verses, setVerses] = useState([]);
  const [versesOpen, setVersesOpen] = useState(false);
  const [ws, setWs] = useState(null);
  const [wsStatus, setWsStatus] = useState('connecting');
  const [uiError, setUiError] = useState('');
  const [explaining, setExplaining] = useState({});
  const [explanations, setExplanations] = useState({});
  const [explainErrors, setExplainErrors] = useState({});

  const scrollRef = useRef(null);
  const sessionIdRef = useRef(getOrCreateSessionId());
  const retryRef = useRef(0);

  const StatusDot = ({ status }) => (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        status === 'open' ? 'bg-green-400' : status === 'connecting' ? 'bg-yellow-400' : 'bg-red-400'
      }`}
    />
  );

  const scrollToBottom = () => {
    if (scrollRef.current?.scrollTo) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  };

  const connectWS = useCallback(() => {
    setWsStatus('connecting');
    setUiError('');

    const sid = sessionIdRef.current || getOrCreateSessionId();
    sessionIdRef.current = sid;

    const socket = new WebSocket(`${WS_BASE}/${sid}`);
    setWs(socket);

    socket.onopen = () => {
      retryRef.current = 0;
      setWsStatus('open');
    };

    socket.onclose = () => {
      setWsStatus('closed');
      const wait = Math.min(15000, 500 * 2 ** Math.min(retryRef.current++, 5));
      setTimeout(() => connectWS(), wait);
    };

    socket.onerror = () => {
      setWsStatus('closed');
      setUiError('Connection error. Please try reconnecting.');
    };

    socket.onmessage = evt => {
      try {
        const data = JSON.parse(evt.data);

        if (data?.type === 'ping') return;

        if (data?.type === 'error' && !data.payload?.for) {
          setIsTyping(false);
          setUiError(data?.message || 'Something went wrong. Please try again.');
          return;
        }

        if (data.type === 'explain' && data.payload) {
          const { for: vid, text } = data.payload;
          setExplanations(prev => ({ ...prev, [vid]: text }));
          setExplaining(prev => ({ ...prev, [vid]: 'done' }));
          setExplainErrors(prev => {
            const next = { ...prev };
            delete next[vid];
            return next;
          });
          return;
        }

        if ((data.type === 'explain_error' || data.type === 'error') && data.payload?.for) {
          const vid = data.payload.for;
          const message = data.payload.message || 'Could not explain this verse. Please try again.';
          setExplaining(prev => ({ ...prev, [vid]: 'done' }));
          setExplainErrors(prev => ({ ...prev, [vid]: message }));
          return;
        }

        const content = data.message || data.response || '';
        if (!content) return;

        if (data.sender === 'ai') {
          setIsTyping(false);
          setUiError('');

          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.id === 'temp-bot-response') {
              const next = [...prev];
              next[next.length - 1] = { id: Date.now(), role: 'bot', content };
              return next;
            }
            return [...prev, { id: Date.now(), role: 'bot', content }];
          });

          if (Array.isArray(data.cited_verses) && data.cited_verses.length) {
            const items = data.cited_verses.map((v, i) => ({
              id: v.id || `${Date.now()}-${i}`,
              reference: v.reference || v.ref || 'Reference',
              text: v.text || v.verse || ''
            }));
            setVerses(items);
            setVersesOpen(true);
            setExplanations({});
            setExplaining({});
            setExplainErrors({});
          } else {
            setVerses([]);
          }
          scrollToBottom();
        }
      } catch (e) {
        setUiError('Bad response from server.');
      }
    };

    return () => socket.close();
  }, []);

  useEffect(() => {
    const cleanup = connectWS();
    return cleanup;
  }, [connectWS]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const sendMessage = useCallback(
    e => {
      e.preventDefault();
      const trimmedInput = input.trim();
      if (!trimmedInput || isTyping || !ws || ws.readyState !== WebSocket.OPEN) return;

      setUiError('');

      const newUserMessage = { id: Date.now(), role: 'user', content: trimmedInput };
      setMessages(prev => [...prev, newUserMessage]);
      setInput('');
      setIsTyping(true);

      setVerses([]);
      setVersesOpen(false);
      setExplanations({});
      setExplaining({});
      setExplainErrors({});

      const tempBotMessage = { id: 'temp-bot-response', role: 'bot', content: ' ' };
      setMessages(prev => [...prev, tempBotMessage]);

      ws.send(JSON.stringify({ message: trimmedInput }));
    },
    [input, isTyping, ws]
  );

  const askExplain = v => {
    if (!ws || ws.readyState !== WebSocket.OPEN || explaining[v.id] === 'loading') return;

    setExplainErrors(prev => {
      const next = { ...prev };
      delete next[v.id];
      return next;
    });
    setExplaining(prev => ({ ...prev, [v.id]: 'loading' }));

    ws.send(
      JSON.stringify({
        type: 'explain',
        verseId: v.id,
        verseText: v.text,
        reference: v.reference,
        query: messages.filter(m => m.role === 'user').slice(-1)[0]?.content || ''
      })
    );
  };

  const wsNotOpen = !ws || ws.readyState !== WebSocket.OPEN;

  const Message = ({ message }) => {
    const isUser = message.role === 'user';
    const isLoading = message.id === 'temp-bot-response';

    return (
      <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'} animate-fadeIn`}>
        <div
          className={`flex items-start max-w-[80%] space-x-3 ${
            isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'
          }`}
        >
          <div
            className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center shadow-lg ${
              isUser
                ? 'bg-white text-black'
                : 'bg-gradient-to-br from-gray-800 to-gray-900 text-white border border-white/10'
            }`}
          >
            {isUser ? <User size={20} /> : <img src={logoImg} alt="AI" className="w-6 h-6 object-contain" />}
          </div>
          <div
            className={`relative group ${
              isUser
                ? 'bg-white text-black rounded-2xl rounded-br-md shadow-xl'
                : 'bg-gradient-to-br from-gray-900/90 to-black/90 text-white rounded-2xl rounded-tl-md border border-white/10 backdrop-blur-sm shadow-xl'
            } ${isLoading ? 'opacity-70' : ''}`}
          >
            <div className="px-5 py-4 break-words overflow-hidden">
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin text-white/60" />
                  <span className="text-sm text-white/60">Thinking...</span>
                </div>
              ) : message.role === 'bot' ? (
                <div className="prose prose-invert max-w-none text-[15px] leading-relaxed break-words [&>p]:break-words [&>*]:break-words [&>p]:mb-3 [&>p:last-child]:mb-0">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => (
                        <p className="mb-3 last:mb-0 break-words text-gray-100">{children}</p>
                      ),
                      strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                      em: ({ children }) => <em className="italic text-gray-200">{children}</em>,
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-white/20 pl-4 italic text-gray-300">
                          {children}
                        </blockquote>
                      )
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-950 to-black flex items-center justify-center p-4">
      <div className="w-full max-w-7xl h-[92vh] flex bg-gradient-to-br from-gray-900/40 to-black/60 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl overflow-hidden">
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Premium Header */}
          <div className="px-6 py-4 border-b border-white/10 bg-gradient-to-r from-black/60 to-gray-900/60 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={onBack}
                  className="text-gray-400 hover:text-white transition-all hover:scale-110 p-2 rounded-xl hover:bg-white/5"
                >
                  <ArrowRight className="w-5 h-5 rotate-180" />
                </button>
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className="absolute inset-0 bg-white/20 blur-md rounded-full"></div>
                    <div className="relative w-10 h-10 bg-gradient-to-br from-gray-800 to-gray-900 rounded-full flex items-center justify-center border border-white/20 shadow-lg">
                      <img src={logoImg} alt="Preacher AI" className="w-6 h-6 object-contain" />
                    </div>
                  </div>
                  <div>
                    <h1 className="text-lg font-semibold text-white">Preacher AI</h1>
                    <p className="text-xs text-gray-400 flex items-center gap-2">
                      <StatusDot status={wsStatus} />
                      <span className="capitalize">{wsStatus}</span>
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm">
                  <span className="text-xs font-medium text-gray-300">Pastoral Mode</span>
                </div>
                <button
                  onClick={connectWS}
                  className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white border border-white/10 rounded-xl hover:bg-white/5 transition-all hover:border-white/20"
                >
                  Reconnect
                </button>
                <button
                  onClick={() => setVersesOpen(v => !v)}
                  className={`px-4 py-2 text-sm font-medium rounded-xl transition-all ${
                    versesOpen
                      ? 'bg-white text-black shadow-lg'
                      : 'text-gray-300 hover:text-white border border-white/10 hover:bg-white/5 hover:border-white/20'
                  }`}
                >
                  <BookOpen className="w-4 h-4 inline mr-2" />
                  Verses
                </button>
              </div>
            </div>
          </div>

          {/* Chat Messages Area */}
          <div className="flex-1 overflow-hidden">
            <div ref={scrollRef} className="h-full overflow-y-auto px-6 py-8 scroll-smooth">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="relative mb-6">
                    <div className="absolute inset-0 bg-white/20 blur-2xl rounded-full"></div>
                    <div className="relative w-20 h-20 bg-gradient-to-br from-gray-800 to-gray-900 rounded-full flex items-center justify-center border border-white/20 shadow-xl">
                      <img src={logoImg} alt="Preacher AI" className="w-12 h-12 object-contain" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-semibold text-white mb-2">Welcome to Preacher AI</h3>
                  <p className="text-gray-400 max-w-md">
                    Ask for biblical insights, sermon preparation, or spiritual guidance.
                  </p>
                </div>
              ) : (
                messages.map(msg => <Message key={msg.id} message={msg} />)
              )}
            </div>
          </div>

          {/* Premium Input Area */}
          <div className="px-6 py-5 border-t border-white/10 bg-gradient-to-r from-black/80 to-gray-900/80 backdrop-blur-sm">
            {uiError && (
              <div className="mb-4 p-4 rounded-xl border bg-red-900/20 border-red-500/30 text-red-200 text-sm flex items-center justify-between backdrop-blur-sm">
                <span>{uiError}</span>
                <button
                  onClick={connectWS}
                  className="ml-4 px-3 py-1.5 text-xs font-medium border border-red-400/30 rounded-lg hover:bg-red-900/30 transition-all"
                >
                  Reconnect
                </button>
              </div>
            )}

            <form onSubmit={sendMessage} className="flex items-end gap-3">
              <div className="flex-1 relative">
                <textarea
                  className="w-full resize-none px-5 py-4 bg-gray-900/60 border border-white/10 rounded-2xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/20 transition-all backdrop-blur-sm text-[15px] leading-relaxed"
                  placeholder={
                    wsNotOpen
                      ? 'Connecting to server...'
                      : 'Ask me anything about scripture, theology, or pastoral care...'
                  }
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage(e);
                    }
                  }}
                  disabled={isTyping || wsNotOpen}
                  rows={1}
                  style={{ minHeight: '56px', maxHeight: '120px' }}
                />
              </div>
              <button
                type="submit"
                className={`flex-shrink-0 w-14 h-14 rounded-2xl flex items-center justify-center transition-all shadow-lg ${
                  !input.trim() || isTyping || wsNotOpen
                    ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                    : 'bg-white hover:bg-gray-100 text-black hover:scale-105 shadow-white/20'
                }`}
                disabled={!input.trim() || isTyping || wsNotOpen}
              >
                {isTyping ? <Loader2 className="h-6 w-6 animate-spin" /> : <Send className="h-5 w-5" />}
              </button>
            </form>
          </div>
        </div>

        {/* Premium Verses Panel */}
        <div
          className={`w-[440px] border-l border-white/10 bg-gradient-to-br from-black/80 to-gray-900/80 backdrop-blur-xl flex flex-col transition-all duration-300 ${
            versesOpen ? 'translate-x-0' : 'translate-x-full absolute right-0 h-full'
          }`}
        >
          {/* Verses Header */}
          <div className="px-6 py-5 border-b border-white/10 bg-gradient-to-r from-black/60 to-gray-900/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-white/5 border border-white/10">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Relevant Verses</h3>
                  <p className="text-xs text-gray-400">
                    {verses.length} {verses.length === 1 ? 'verse' : 'verses'} found
                  </p>
                </div>
              </div>
              <button
                onClick={() => setVersesOpen(false)}
                className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Verses Content */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {verses.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                  <BookOpen className="w-8 h-8 text-gray-500" />
                </div>
                <p className="text-sm text-gray-400">
                  No verses yet. Start a conversation to see biblical references.
                </p>
              </div>
            ) : (
              verses.map(v => (
                <div
                  key={v.id}
                  className="group relative bg-gradient-to-br from-gray-900/60 to-black/60 border border-white/10 rounded-2xl p-5 backdrop-blur-sm hover:border-white/20 transition-all duration-300 hover:shadow-xl"
                >
                  {/* Verse Reference */}
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-semibold text-white text-sm">{v.reference}</h4>
                    <button
                      onClick={() => {
                        // Using document.execCommand as navigator.clipboard.writeText may not work in iframes
                        const textToCopy = `${v.reference} — ${v.text}`;
                        const textArea = document.createElement('textarea');
                        textArea.value = textToCopy;
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        try {
                          document.execCommand('copy');
                        } catch (err) {
                          console.error('Failed to copy text: ', err);
                        }
                        document.body.removeChild(textArea);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
                      title="Copy verse"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                    </button>
                  </div>

                  {/* Verse Text */}
                  <p className="text-[13px] leading-relaxed text-gray-300 italic mb-4 border-l-2 border-white/20 pl-3">
                    "{v.text}"
                  </p>

                  {/* Action Button */}
                  <button
                    onClick={() => askExplain(v)}
                    disabled={explaining[v.id] === 'loading'}
                    className={`w-full px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      explaining[v.id] === 'loading'
                        ? 'bg-white/5 text-gray-400 cursor-wait'
                        : 'bg-white/10 hover:bg-white/20 text-white border border-white/10 hover:border-white/20'
                    }`}
                  >
                    {explaining[v.id] === 'loading' ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating explanation...
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <Sparkles className="h-4 w-4" />
                        Why is this relevant?
                      </span>
                    )}
                  </button>

                  {/* Error Display */}
                  {explainErrors[v.id] && (
                    <div className="mt-3 p-3 rounded-xl bg-red-900/20 border border-red-500/30 backdrop-blur-sm">
                      <p className="text-xs text-red-200 mb-2">{explainErrors[v.id]}</p>
                      <button
                        onClick={() => askExplain(v)}
                        disabled={explaining[v.id] === 'loading'}
                        className="text-xs font-medium text-red-300 hover:text-red-200 underline"
                      >
                        Try again
                      </button>
                    </div>
                  )}

                  {/* Explanation Display */}
                  {explanations[v.id] && (
                    <div className="mt-4 pt-4 border-t border-white/10">
                      <div className="flex items-start gap-2 mb-2">
                        <Info className="w-4 h-4 text-white/60 flex-shrink-0 mt-0.5" />
                        <span className="text-xs font-semibold text-white/80 uppercase tracking-wide">
                          Explanation
                        </span>
                      </div>
                      <p className="text-[13px] leading-relaxed text-gray-300">{explanations[v.id]}</p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.4s ease-out;
        }
        textarea {
          field-sizing: content;
        }
      `}</style>
    </div>
  );
}

// Main App Component
export default function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing' or 'chat'

  return (
    <>
      {currentView === 'landing' ? (
        <LandingPage onGetStarted={() => setCurrentView('chat')} />
      ) : (
        <ChatInterface onBack={() => setCurrentView('landing')} />
      )}
    </>
  );
}