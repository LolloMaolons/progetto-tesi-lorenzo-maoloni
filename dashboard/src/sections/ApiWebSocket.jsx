import React, { useRef, useEffect } from 'react';
import { Box, Paper, Typography, TextField, Button, Divider, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import WebIcon from '@mui/icons-material/Web';
import { useWebSocketCtx } from './WebSocketContext';

export default function ApiWebSocket() {

  const { url, setUrl, connected, messages, connect, disconnect, setMessages } = useWebSocketCtx();
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>WebSocket Notifications</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField label="WebSocket URL" value={url} onChange={e => setUrl(e.target.value)} fullWidth />
        <Button
          variant="contained"
          color={connected ? 'secondary' : 'primary'}
          startIcon={<PlayArrowIcon />}
          onClick={connected ? disconnect : () => { setMessages([]); connect(); }}
        >
          {connected ? 'Disconnect' : 'Connect'}
        </Button>
      </Box>
      <Divider sx={{ my: 2 }} />
      <Typography variant="subtitle2" color="text.secondary">Messages</Typography>
      <List ref={listRef} sx={{ bgcolor: '#f5f5f5', borderRadius: 1, minHeight: 120, maxHeight: 300, overflow: 'auto' }}>
        {messages.map((msg, i) => (
          <ListItem key={i}>
            <ListItemIcon><WebIcon color="primary" /></ListItemIcon>
            <ListItemText primary={msg} />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
