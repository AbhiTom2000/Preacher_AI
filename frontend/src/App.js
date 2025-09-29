import { useEffect, useState, useRef } from 'react';
import './App.css';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { Input } from './components/ui/input';
import { Button } from './components/ui/button';
import { Toaster } from './components/ui/toaster';  // ✅ Correct
import { useToast } from './hooks/use-toast';       // ✅ Correct

import { ScrollArea } from './components/ui/scroll-area';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { TypeAnimation } from 'react-type-animation';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    const storedSessionId = localStorage.getItem('preacher_ai_session_id');
    if (storedSessionId) {
      setSessionId(storedSessionId);
    } else {
      fetch(`${process.env.REACT_APP_API_BASE_URL}/api/session`, {
        method: 'POST',
      })
        .then(response => response.json())
        .then(data => {
          if (data.session_id) {
            setSessionId(data.session_id);
            localStorage.setItem('preacher_ai_session_id', data.session_id);
          }
        })
        .catch(error => {
          console.error('Error creating session:', error);
          toast({
            title: "Connection Error",
            description: "Failed to create a new session. Please refresh the page.",
            variant: "destructive",
          });
        });
    }
  }, [toast]);

  // NEW: WebSocket connection logic
  useEffect(() => {
    if (!sessionId) return;
    
    let ws = null;
    let timeoutId = null;

    const connectWebSocket = () => {
      ws = new WebSocket(`${process.env.REACT_APP_WEBSOCKET_URL}/ws/chat/${sessionId}`);

      ws.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttemptsRef.current = 0;
        setLoading(false);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        setMessages(prevMessages => [...prevMessages, message]);
        setLoading(false);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event);
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
          timeoutId = setTimeout(() => {
            reconnectAttemptsRef.current++;
            console.log(`Attempting to reconnect... attempt ${reconnectAttemptsRef.current}`);
            connectWebSocket();
          }, delay);
        } else {
          toast({
            title: "Connection Lost",
            description: "Chat connection lost. Please refresh the page.",
            variant: "destructive",
          });
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws.close();
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      clearTimeout(timeoutId);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId, toast]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast({
        title: "Connection Status",
        description: "Please wait for the connection to be established.",
        variant: "destructive",
      });
      return;
    }

    const userMessage = {
      message: input,
      sender: 'user',
      sessionId: sessionId,
      timestamp: new Date().toISOString()
    };
    
    setLoading(true);
    setInput('');
    
    // Send message via WebSocket
    wsRef.current.send(JSON.stringify(userMessage));
  };

  const getAvatarFallback = (sender) => {
    if (sender === 'ai') return 'AI';
    return 'You';
  };

  const isAiSpeaking = messages.length > 0 && messages[messages.length - 1].sender === 'ai' && loading;

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center p-4 bg-gray-50 dark:bg-gray-950">
      <Toaster />
      <Card className="w-full max-w-2xl h-full flex flex-col bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 rounded-xl shadow-lg">
        <CardHeader className="border-b p-4 border-gray-200 dark:border-gray-800 flex flex-row items-center justify-between">
          <CardTitle className="text-xl font-bold text-gray-900 dark:text-gray-50">Preacher.ai</CardTitle>
          <CardDescription className="text-sm text-gray-500 dark:text-gray-400">Your gentle spiritual companion</CardDescription>
        </CardHeader>
        <CardContent className="flex-1 p-4 overflow-y-auto">
          <ScrollArea className="h-full">
            <div className="space-y-4">
              {messages.map((msg, index) => (
                <div key={index} className={`flex items-start gap-4 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
                  {msg.sender === 'ai' && (
                    <Avatar className="w-8 h-8">
                      <AvatarImage src="/placeholder-user.jpg" />
                      <AvatarFallback className="bg-blue-500 text-white dark:bg-blue-600">AI</AvatarFallback>
                    </Avatar>
                  )}
                  <div
                    className={`rounded-lg p-3 max-w-[80%] ${
                      msg.sender === 'user'
                        ? 'bg-blue-500 text-white dark:bg-blue-600'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-50'
                    }`}
                  >
                    <Markdown remarkPlugins={[remarkGfm]}>{msg.message}</Markdown>
                    {msg.cited_verses && msg.cited_verses.length > 0 && (
                      <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                        <h4 className="font-semibold">Cited Verses:</h4>
                        <ul className="list-disc list-inside">
                          {msg.cited_verses.map((verse, vIndex) => (
                            <li key={vIndex}>{verse.reference}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  {msg.sender === 'user' && (
                    <Avatar className="w-8 h-8">
                      <AvatarImage src="/placeholder-user.jpg" />
                      <AvatarFallback className="bg-gray-500 text-white dark:bg-gray-700">You</AvatarFallback>
                    </Avatar>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex items-start gap-4">
                  <Avatar className="w-8 h-8">
                    <AvatarImage src="/placeholder-user.jpg" />
                    <AvatarFallback className="bg-blue-500 text-white dark:bg-blue-600">AI</AvatarFallback>
                  </Avatar>
                  <div className="rounded-lg p-3 max-w-[80%] bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-50">
                    <TypeAnimation
                      sequence={[
                        '...',
                        1000,
                        '',
                      ]}
                      wrapper="span"
                      cursor={true}
                      repeat={Infinity}
                      speed={50}
                      deletionSpeed={90}
                    />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </CardContent>
        <CardFooter className="p-4 border-t border-gray-200 dark:border-gray-800">
          <form className="flex w-full space-x-2" onSubmit={handleSubmit}>
            <Input
              className="flex-1"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <Button type="submit" disabled={loading}>
              Send
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  );
}

export default App;