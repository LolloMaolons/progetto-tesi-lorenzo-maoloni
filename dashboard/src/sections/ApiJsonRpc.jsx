
import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, TextField, Button, Divider, IconButton, List, ListItem, ListItemButton, ListItemText, ListItemIcon, Tooltip } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import DescriptionIcon from '@mui/icons-material/Description';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';
import { saveRequests, loadRequests } from './requestStore';

const DEFAULTS = [
  {
    name: 'Discount prodotto id 1',
    body: '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "discountProduct",\n  "params": { "id": 1, "discount": 10, "threshold": 25}\n}',
  },
  {
    name: 'Reset prodotto id 1',
    body: '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "resetProduct",\n  "params": { "id": 1, "threshold": 25 }\n}',
  },
  {
    name: 'Discount all low stock',
    body: '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "discountAllLowStock",\n  "params": { "discount": 10, "threshold": 25 }\n}',
  },
  {
    name: 'Reset all high stock',
    body: '{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "resetAllHighStock",\n  "params": { "threshold": 25 }\n}',
  },
];

export default function ApiJsonRpc() {
  const [requests, setRequests] = useState(() => loadRequests('jsonrpc-requests', DEFAULTS));
  const [selected, setSelected] = useState(0);
  const [url, setUrl] = useState('http://localhost:5000/rpc');
  const [body, setBody] = useState(requests[0].body);
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSave, setShowSave] = useState(false);

  useEffect(() => {
    setBody(requests[selected].body);
    setShowSave(false);
  }, [selected, requests]);

  useEffect(() => {
    const isPreset = requests.some(r => r.body === body);
    setShowSave(!isPreset && body);
  }, [body, requests]);

  const handleSend = async () => {
    setLoading(true);
    setResponse('');
    try {
      const res = await axios.post(url, JSON.parse(body), { headers: { 'Content-Type': 'application/json' } });
      setResponse(JSON.stringify(res.data, null, 2));
    } catch (err) {
      setResponse(err.response ? JSON.stringify(err.response.data, null, 2) : err.message);
    }
    setLoading(false);
  };

  const handleSelect = idx => {
    setSelected(idx);
  };

  const handleAdd = () => {
    setBody('');
    setShowSave(false);
  };

  const handleSave = () => {
    const newReq = { name: `Custom JSON-RPC ${requests.length + 1}`, body };
    const newList = [...requests, newReq];
    setRequests(newList);
    saveRequests('jsonrpc-requests', newList);
    setSelected(newList.length - 1);
    setShowSave(false);
  };

  const handleDelete = idx => {
    if (idx < DEFAULTS.length) return;
    const newList = requests.filter((_, i) => i !== idx);
    setRequests(newList);
    saveRequests('jsonrpc-requests', newList);
    setSelected(Math.max(0, idx - 1));
  };

  const handleResetDefaults = () => {
    setRequests(DEFAULTS);
    saveRequests('jsonrpc-requests', DEFAULTS);
    setSelected(0);
    setBody(DEFAULTS[0].body);
    setShowSave(false);
  };

  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      <Paper elevation={1} sx={{ minWidth: 260, maxWidth: 320, p: 1, mr: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, mt: 1, fontWeight: 700 }}>Requests</Typography>
        <List dense>
          {requests.map((req, i) => (
            <ListItem key={i} disablePadding
              secondaryAction={i >= DEFAULTS.length ? (
                <Tooltip title="Rimuovi richiesta personalizzata">
                  <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(i)} size="small">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              ) : null}
            >
              <ListItemButton selected={selected === i} onClick={() => handleSelect(i)}>
                <ListItemIcon><DescriptionIcon color={selected === i ? 'primary' : 'action'} /></ListItemIcon>
                <ListItemText primary={req.name} secondary={req.body.slice(0, 40) + (req.body.length > 40 ? '...' : '')} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Button startIcon={<AddIcon />} onClick={handleAdd} variant="outlined" sx={{ mt: 1 }}>Nuova richiesta</Button>
        <Button color="error" variant="outlined" sx={{ mt: 1 }} onClick={handleResetDefaults}>
          Ripristina richieste di default
        </Button>
      </Paper>
      <Paper elevation={2} sx={{ flex: 1, p: 3, minWidth: 0 }}>
        <Typography variant="h6" gutterBottom>JSON-RPC Tool</Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField label="Endpoint" value={url} onChange={e => setUrl(e.target.value)} fullWidth />
          <IconButton color="primary" onClick={handleSend} disabled={loading} size="large">
            <SendIcon />
          </IconButton>
        </Box>
        <TextField
          label="Request Body (JSON-RPC)"
          value={body}
          onChange={e => setBody(e.target.value)}
          multiline
          minRows={5}
          fullWidth
          sx={{ mb: 2 }}
        />
        {showSave && (
          <Button startIcon={<SaveIcon />} onClick={handleSave} color="primary" variant="contained" sx={{ mb: 2 }}>
            Salva richiesta
          </Button>
        )}
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" color="text.secondary">Response</Typography>
        <Box sx={{ bgcolor: '#f5f5f5', borderRadius: 1, p: 2, minHeight: 120, fontFamily: 'monospace', fontSize: 15, whiteSpace: 'pre-wrap' }}>
          {response}
        </Box>
      </Paper>
    </Box>
  );
}
