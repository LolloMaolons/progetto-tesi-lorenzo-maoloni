import WebSocket from 'ws';
const wsUrl = process.env.WS_URL || 'ws://localhost:7070/ws';
const ws = new WebSocket(wsUrl);

ws.on('open', () => console.log(`[${Date.now()}] WS connected to ${wsUrl}`));
ws.on('message', (data) => {
  const ts = Date.now();
  console.log(`[${ts}] recv ${data.toString()}`);
});