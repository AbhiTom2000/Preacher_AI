import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import { Button } from './components/ui/button';
import { Textarea } from './components/ui/textarea';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './components/ui/card';
import { ScrollArea } from './components/ui/scroll-area';
import { Loader2, Send, Bot, User, Info } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- CONFIGURATION ---
const WS_BASE = process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000/ws/chat';
const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Copy-all helper (Markdown)
function versesToMarkdown(verses) {
  if (!Array.isArray(verses) || !verses.length) return '';
  return verses.map(v => `- *${v.reference}*: “${v.text}”`).join('\n');
}

// --- analytics (simple, privacy-friendly) ---
const ANALYTICS_URL = (process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000') + '/api/analytics/events';

function makeEvent(sessionId, type, props = {}) {
  return { type, ts: Date.now(), session_id: sessionId || 'unknown', props };
}

async function sendEvents(events) {
  try {
    const body = JSON.stringify({ events });
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      const ok = navigator.sendBeacon(ANALYTICS_URL, blob);
      if (ok) return;
    }
    await fetch(ANALYTICS_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
  } catch {
    // ignore analytics failures
  }
}

// tiny UUIDv4
const uuidv4 = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });

// Persist session across refreshes
const SESSION_KEY = 'preacher_session_id';
function getOrCreateSessionId() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = uuidv4();
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);            // {id, role: 'user'|'bot', content}
  const [isTyping, setIsTyping] = useState(false);
  const [verses, setVerses] = useState([]);                // [{id, reference, text}]
  const [versesOpen, setVersesOpen] = useState(false);
  const [ws, setWs] = useState(null);
  const [wsStatus, setWsStatus] = useState('connecting');  // 'connecting' | 'open' | 'closed'
  const [uiError, setUiError] = useState('');

  const [explaining, setExplaining] = useState({});        // { [id]: 'loading'|'done' }
  const [explanations, setExplanations] = useState({});    // { [id]: string }
  const [explainErrors, setExplainErrors] = useState({});  // { [id]: string }

  const explainTimersRef = useRef({});                     // { [id]: timeoutId }
  const explainStartRef = useRef({});                      // { [id]: msStart }
  const lastUserMsgRef = useRef('');                       // last sent user msg
  const rttRef = useRef(null);                             // user->AI roundtrip
  const scrollRef = useRef(null);
  const sessionIdRef = useRef(getOrCreateSessionId());     // stable across reloads
  const retryRef = useRef(0);                              // WS backoff counter

  // Status dot
  const StatusDot = ({ status }) => (
    <span
      title={status}
      className={`inline-block w-2.5 h-2.5 rounded-full ${
        status === 'open' ? 'bg-green-500'
        : status === 'connecting' ? 'bg-yellow-500'
        : 'bg-red-500'
      }`}
    />
  );

  const lastUserQuery = () => {
    const m = [...messages].reverse().find(x => x.role === 'user');
    return m ? m.content : '';
  };

  const scrollToBottom = () => {
    if (scrollRef.current?.scrollTo) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  };

  // Connect WS with exponential backoff reconnect
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
      sendEvents([ makeEvent(sessionIdRef.current, 'ws_open') ]);
    };

    socket.onclose = () => {
      setWsStatus('closed');
      sendEvents([ makeEvent(sessionIdRef.current, 'ws_closed') ]);
      // backoff reconnect
      const wait = Math.min(15000, 500 * 2 ** Math.min(retryRef.current++, 5));
      setTimeout(() => connectWS(), wait);
    };

    socket.onerror = () => {
      setWsStatus('closed');
      setUiError('Connection error. Please try reconnecting.');
      sendEvents([ makeEvent(sessionIdRef.current, 'ws_error') ]);
    };

    socket.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);

        if (data?.type === 'ping') return; // heartbeat

        // Typed top-level error
        if (data?.type === 'error') {
          setIsTyping(false);
          setUiError(data?.message || 'Something went wrong. Please try again.');
          return;
        }

        // Typed explain success
        if (data.type === 'explain' && data.payload) {
          const { for: vid, text } = data.payload;
          setExplanations(prev => ({ ...prev, [vid]: text }));
          setExplaining(prev => ({ ...prev, [vid]: 'done' }));

          if (explainTimersRef.current[vid]) {
            clearTimeout(explainTimersRef.current[vid]);
            delete explainTimersRef.current[vid];
          }
          setExplainErrors(prev => {
            const next = { ...prev };
            delete next[vid];
            return next;
          });

          const ms = explainStartRef.current[vid] ? (performance.now() - explainStartRef.current[vid]) : null;
          if (ms) sendEvents([ makeEvent(sessionIdRef.current, 'explain_success', { verse_id: vid, ms: Math.round(ms), length: (text || '').length }) ]);
          delete explainStartRef.current[vid];
          return;
        }

        // Typed explain error
        if ((data.type === 'explain_error' || data.type === 'error') && data.payload?.for) {
          const vid = data.payload.for;
          const message = data.payload.message || 'Could not explain this verse. Please try again.';
          setExplaining(prev => ({ ...prev, [vid]: 'done' }));
          if (explainTimersRef.current[vid]) {
            clearTimeout(explainTimersRef.current[vid]);
            delete explainTimersRef.current[vid];
          }
          setExplainErrors(prev => ({ ...prev, [vid]: message }));

          const ms = explainStartRef.current[vid] ? (performance.now() - explainStartRef.current[vid]) : null;
          sendEvents([ makeEvent(sessionIdRef.current, 'explain_error', { verse_id: vid, ms: ms ? Math.round(ms) : null }) ]);
          delete explainStartRef.current[vid];
          return;
        }

        // Regular chat message path
        const content = data.message || data.response || '';
        if (!content) return;

        if (data.sender === 'ai') {
          setIsTyping(false);
          setUiError('');

          const rtt = rttRef.current ? (performance.now() - rttRef.current) : null;
          if (rtt) sendEvents([ makeEvent(sessionIdRef.current, 'ai_response_received', { ms: Math.round(rtt), has_verses: Array.isArray(data.cited_verses) && data.cited_verses.length > 0 }) ]);

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
      } catch {
        setUiError('Bad response from server.');
      }
    };

    return () => socket.close();
  }, []);

  useEffect(() => {
    const cleanup = connectWS();
    return cleanup;
  }, [connectWS]);

  useEffect(() => { scrollToBottom(); }, [messages, isTyping]);

  const sendMessage = useCallback((e) => {
    e.preventDefault();
    const trimmedInput = input.trim();
    if (!trimmedInput || isTyping || !ws || ws.readyState !== WebSocket.OPEN) return;

    setUiError('');
    lastUserMsgRef.current = trimmedInput;
    rttRef.current = performance.now();
    sendEvents([ makeEvent(sessionIdRef.current, 'message_sent', { length: trimmedInput.length }) ]);

    const newUserMessage = { id: Date.now(), role: 'user', content: trimmedInput };
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setIsTyping(true);

    setVerses([]);
    setVersesOpen(false);
    setExplanations({});
    setExplaining({});
    setExplainErrors({});
    Object.values(explainTimersRef.current).forEach(id => clearTimeout(id));
    explainTimersRef.current = {};

    const tempBotMessage = { id: 'temp-bot-response', role: 'bot', content: ' ' };
    setMessages(prev => [...prev, tempBotMessage]);

    ws.send(JSON.stringify({ message: trimmedInput }));
  }, [input, isTyping, ws]);

  const askExplain = (v) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (explaining[v.id] === 'loading') return;

    setExplainErrors(prev => {
      const next = { ...prev };
      delete next[v.id];
      return next;
    });
    setExplaining(prev => ({ ...prev, [v.id]: 'loading' }));

    explainStartRef.current[v.id] = performance.now();
    sendEvents([ makeEvent(sessionIdRef.current, 'explain_request', { verse_id: v.id }) ]);

    if (explainTimersRef.current[v.id]) clearTimeout(explainTimersRef.current[v.id]);
    explainTimersRef.current[v.id] = setTimeout(() => {
      setExplaining(prev => ({ ...prev, [v.id]: 'done' }));
      setExplainErrors(prev => ({ ...prev, [v.id]: 'This is taking longer than expected. Please try again.' }));
      const started = explainStartRef.current[v.id];
      sendEvents([ makeEvent(sessionIdRef.current, 'explain_timeout', { verse_id: v.id, ms: started ? Math.round(performance.now() - started) : 20000 }) ]);
      delete explainStartRef.current[v.id];
    }, 20000);

    ws.send(JSON.stringify({
      type: 'explain',
      verseId: v.id,
      verseText: v.text,
      reference: v.reference,
      query: lastUserQuery()
    }));
  };

  const wsNotOpen = !ws || ws.readyState !== WebSocket.OPEN;

  const Message = ({ message }) => {
    const isUser = message.role === 'user';
    const isLoading = message.id === 'temp-bot-response';

    return (
      <div className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`flex items-start max-w-[75%] space-x-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
            {isUser ? <User size={18} /> : <Bot size={18} />}
          </div>
          <Card className={`p-3 rounded-xl shadow-lg transition-all duration-300 ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-none'
              : 'bg-secondary rounded-tl-none border-secondary'
          } ${isLoading ? 'opacity-70' : ''}`}>
            {isLoading
              ? <Loader2 className="h-5 w-5 animate-spin" />
              : (
                message.role === 'bot' ? (
                  <div className="prose prose-invert max-w-none text-sm">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" />,
                        code: ({ inline, className, children, ...props }) =>
                          inline
                            ? <code className="px-1 py-0.5 rounded bg-black/20" {...props}>{children}</code>
                            : <code className="block p-3 rounded bg-black/40 overflow-x-auto" {...props}>{children}</code>
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                )
              )
            }
          </Card>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-4xl h-[90vh] flex flex-col shadow-2xl relative">
        {/* Header */}
        <CardHeader className="p-4 border-b flex items-center justify-between">
          <CardTitle className="flex items-center text-xl font-bold text-gray-800">
            <Bot className="w-6 h-6 mr-2 text-primary" />
            Preacher AI Chatbot
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-1 rounded bg-violet-100 text-violet-700 border border-violet-200">
              Pastoral Mode
            </span>
            <div className="flex items-center gap-1 text-xs text-gray-600">
              <StatusDot status={wsStatus} /> {wsStatus}
            </div>
            <Button
              variant="outline"
              onClick={() => { connectWS(); sendEvents([ makeEvent(sessionIdRef.current, 'ws_reconnect_click') ]); }}
              title="Reconnect"
            >
              Reconnect
            </Button>
            <Button
              variant="outline"
              className={versesOpen ? 'bg-primary text-primary-foreground' : ''}
              onClick={() => setVersesOpen(v => !v)}
              title="Toggle relevant verses"
            >
              Verses
            </Button>
          </div>
        </CardHeader>

        {/* Chat Window */}
        <CardContent className="flex-1 overflow-hidden p-4">
          <ScrollArea ref={scrollRef} className="h-full pr-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                <Bot className="w-12 h-12 mb-4 text-primary opacity-50" />
                <p>Start a conversation with Preacher AI.</p>
                <p className="text-sm">Ask for a sermon, biblical insights, or devotional content.</p>
              </div>
            ) : (
              messages.map((msg) => (
                <Message key={msg.id} message={msg} />
              ))
            )}
          </ScrollArea>
        </CardContent>

        {/* Input + Error Bar */}
        <CardFooter className="p-4 border-t relative">
          {uiError && (
            <div className="w-full mb-3 p-3 rounded-lg border text-sm bg-red-50 border-red-200 text-red-700 flex items-center justify-between">
              <span>{uiError}</span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => connectWS()} className="h-8">
                  Reconnect
                </Button>
                <Button
                  onClick={() => {
                    if (lastUserMsgRef.current && ws && ws.readyState === WebSocket.OPEN) {
                      setInput(lastUserMsgRef.current);
                      sendEvents([ makeEvent(sessionIdRef.current, 'retry_send_click', { last_len: (lastUserMsgRef.current || '').length }) ]);
                      const fakeEvent = { preventDefault() {} };
                      setTimeout(() => sendMessage(fakeEvent), 0);
                    }
                  }}
                  className="h-8"
                  disabled={!lastUserMsgRef.current || !ws || ws.readyState !== WebSocket.OPEN}
                >
                  Retry
                </Button>
              </div>
            </div>
          )}

          <form onSubmit={sendMessage} className="flex w-full space-x-4">
            <Textarea
              className="flex-1 resize-none p-3 h-12"
              placeholder={wsNotOpen ? 'Connecting…' : 'Type your message here...'}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.nativeEvent.isComposing) return; // IME safety
                if (e.key === 'Enter' && !e.shiftKey) sendMessage(e);
              }}
              disabled={isTyping || wsNotOpen}
            />
            <Button
              type="submit"
              size="icon"
              className="h-12 w-12 rounded-lg"
              disabled={!input.trim() || isTyping || wsNotOpen}
            >
              {isTyping ? <Loader2 className="h-6 w-6 animate-spin" /> : <Send className="h-6 w-6" />}
            </Button>
          </form>

          {wsNotOpen && (
            <div className="absolute -bottom-6 left-0 w-full text-[11px] text-center text-gray-600">
              Connecting to server…
            </div>
          )}
        </CardFooter>

        {/* Slide-in Relevant Verses Panel */}
        <div className={`verses-panel ${versesOpen ? 'visible' : ''}`}>
          <div className="verses-header">
            <h3>Relevant Verses</h3>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <button
                className="menu-btn"
                title="Copy all verses as Markdown"
                onClick={async () => {
                  const md = versesToMarkdown(verses);
                  if (!md) return;
                  try {
                    await navigator.clipboard.writeText(md);
                    sendEvents([ makeEvent(sessionIdRef.current, 'verses_copy_all', { count: verses.length, length: md.length }) ]);
                  } catch { /* ignore */ }
                }}
              >
                Copy all (Markdown)
              </button>
              <button className="close-verses" onClick={() => setVersesOpen(false)}>✕</button>
            </div>
          </div>

          <div className="verses-content">
            {verses.length === 0 ? (
              <div className="text-sm" style={{ opacity: .7 }}>No verses yet. Ask something to see references.</div>
            ) : verses.map(v => (
              <div key={v.id} className="verse-card">
                <div className="verse-reference">{v.reference}</div>
                <div className="verse-text">“{v.text}”</div>

                <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="menu-btn"
                    onClick={() => navigator.clipboard.writeText(`${v.reference} — ${v.text}`)}
                    title="Copy to clipboard"
                  >
                    Copy
                  </button>
                  <button
                    className="menu-btn"
                    onClick={() => askExplain(v)}
                    disabled={explaining[v.id] === 'loading'}
                    title="Why this verse matters for your question"
                  >
                    {explaining[v.id] === 'loading'
                      ? <span><Loader2 className="inline-block mr-1 h-4 w-4 animate-spin" />Explaining…</span>
                      : <span><Info className="inline-block mr-1" size={16} />Why is this relevant?</span>
                    }
                  </button>
                </div>

                {/* Inline error & retry */}
                {explainErrors[v.id] && (
                  <div className="text-sm mt-2 p-2 rounded border border-red-300 bg-red-50 text-red-700 flex items-center justify-between">
                    <span>{explainErrors[v.id]}</span>
                    <button
                      className="menu-btn"
                      onClick={() => askExplain(v)}
                      disabled={explaining[v.id] === 'loading'}
                    >
                      Retry
                    </button>
                  </div>
                )}

                {explanations[v.id] && (
                  <div className="cited-indicator" style={{ marginTop: '0.75rem' }}>
                    {explanations[v.id]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}

export default App;