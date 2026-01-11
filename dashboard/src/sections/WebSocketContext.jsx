import React, { createContext, useContext, useRef, useState } from 'react';

const WebSocketContext = createContext();

export function WebSocketProvider({ children }) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [url, setUrl] = useState('ws://localhost:7070/ws');

  const connect = (customUrl) => {
    if (wsRef.current) wsRef.current.close();
    const ws = new window.WebSocket(customUrl || url);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => setMessages(msgs => [...msgs, e.data]);
    setUrl(customUrl || url);
  };

  const disconnect = () => {
    if (wsRef.current) wsRef.current.close();
    setConnected(false);
  };

  return (
    <WebSocketContext.Provider value={{ wsRef, connected, messages, url, setUrl, connect, disconnect, setMessages }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketCtx() {
  return useContext(WebSocketContext);
}
