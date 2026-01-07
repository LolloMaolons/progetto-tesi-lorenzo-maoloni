
import WebSocket from 'ws';

const WS_URL = process.argv[2] || process.env.WS_URL || 'ws://localhost:7070/ws';
const TOKEN = process.env.JWT_TOKEN || '';

let url = WS_URL;
if (TOKEN) {
  url += `?token=${TOKEN}`;
}

console.log(`Connecting to ${WS_URL}...`);
if (TOKEN) {
  console.log('Using JWT token for authentication');
}

const ws = new WebSocket(url);

ws.on('open', () => {
  console.log('✓ Connected to WebSocket server');
  console.log('Listening for events (Ctrl+C to exit)...\n');
});

ws.on('message', (data) => {
  try {
    const event = JSON.parse(data.toString());
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] Event received:`, JSON.stringify(event, null, 2));
  } catch (err) {
    console.log('Raw message:', data.toString());
  }
});

ws.on('error', (err) => {
  console.error('WebSocket error:', err.message);
});

ws.on('close', () => {
  console.log('\n✗ Connection closed');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('\nClosing connection...');
  ws.close();
});
