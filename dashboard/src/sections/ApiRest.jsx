import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, TextField, Button, MenuItem, Divider, IconButton, List, ListItem, ListItemButton, ListItemText, ListItemIcon, Tooltip } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import DescriptionIcon from '@mui/icons-material/Description';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';
import { saveRequests, loadRequests } from './requestStore';

const methods = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE'];

const DEFAULTS = [
  {
    name: 'Get all products',
    method: 'GET',
    url: 'http://localhost:8080/products',
    body: '',
  },
  {
    name: 'Patch stock (single >25)',
    method: 'PATCH',
    url: 'http://localhost:8080/products/1?stock=60',
    body: '',
  },
  {
    name: 'Patch stock (single <25)',
    method: 'PATCH',
    url: 'http://localhost:8080/products/1?stock=4',
    body: '',
  },
  {
    name: 'Patch stock (multiple >25)',
    method: 'PATCH',
    url: 'http://localhost:8080/products',
    body: '[{"id":1,"stock":100},{"id":9,"stock":80},{"id":10,"stock":128},{"id":19,"stock":128}]',
  },
  {
    name: 'Patch stock (multiple <25)',
    method: 'PATCH',
    url: 'http://localhost:8080/products',
    body: '[{"id":1,"stock":10},{"id":9,"stock":5},{"id":10,"stock":8},{"id":19,"stock":8}]',
  },
  
  {
    name: 'Patch price (single)',
    method: 'PATCH',
    url: 'http://localhost:8080/products/1?price=1349.1',
    body: '',
  },
  {
    name: 'Patch price (multiple)',
    method: 'PATCH',
    url: 'http://localhost:8080/products',
    body: '[{"id":9,"price":719.1},{"id":15,"price":494.1}]',
  },
  {
    name: 'Reset catalog (stock & prices)',
    method: 'POST',
    url: 'http://localhost:8080/reset',
    body: '',
  }
];


export default function ApiRest() {
  const [requests, setRequests] = useState(() => loadRequests('rest-requests', DEFAULTS));
  const [selected, setSelected] = useState(0);
  const [url, setUrl] = useState(requests[0].url);
  const [method, setMethod] = useState(requests[0].method);
  const [body, setBody] = useState(requests[0].body);
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showSave, setShowSave] = useState(false);

  useEffect(() => {
    setUrl(requests[selected].url);
    setMethod(requests[selected].method);
    setBody(requests[selected].body);
    setEditing(false);
    setShowSave(false);
  }, [selected, requests]);

  useEffect(() => {
    const isPreset = requests.some(r => r.url === url && r.method === method && r.body === body);
    setShowSave(!isPreset && (url || body));
    setEditing(true);
  }, [url, method, body, requests]);

  const handleSend = async () => {
    setLoading(true);
    setResponse('');
    try {
      const config = {
        method,
        url,
        headers: { 'Content-Type': 'application/json' },
        ...(body && (method === 'POST' || method === 'PATCH' || method === 'PUT') ? { data: JSON.parse(body) } : {})
      };
      const res = await axios(config);
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
    setUrl('');
    setMethod('GET');
    setBody('');
    setEditing(true);
    setShowSave(false);
  };

  const handleSave = () => {
    const newReq = { name: `Custom ${method} ${url}`, method, url, body };
    const newList = [...requests, newReq];
    setRequests(newList);
    saveRequests('rest-requests', newList);
    setSelected(newList.length - 1);
    setShowSave(false);
  };

  const handleDelete = idx => {
    if (idx < DEFAULTS.length) return;
    const newList = requests.filter((_, i) => i !== idx);
    setRequests(newList);
    saveRequests('rest-requests', newList);
    setSelected(Math.max(0, idx - 1));
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
                <ListItemText primary={req.name} secondary={`${req.method} ${req.url}`} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Button startIcon={<AddIcon />} onClick={handleAdd} variant="outlined" sx={{ mt: 1 }}>Nuova richiesta</Button>
        <Button color="error" variant="outlined" sx={{ mt: 1 }} onClick={() => {
          setRequests(DEFAULTS);
          saveRequests('rest-requests', DEFAULTS);
          setSelected(0);
        }}>Ripristina richieste di default</Button>
      </Paper>
      <Paper elevation={2} sx={{ flex: 1, p: 3, minWidth: 0 }}>
        <Typography variant="h6" gutterBottom>REST API Tester</Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField select label="Method" value={method} onChange={e => setMethod(e.target.value)} sx={{ width: 120 }}>
            {methods.map(m => <MenuItem key={m} value={m}>{m}</MenuItem>)}
          </TextField>
          <TextField label="URL" value={url} onChange={e => setUrl(e.target.value)} fullWidth />
          <IconButton color="primary" onClick={handleSend} disabled={loading} size="large">
            <SendIcon />
          </IconButton>
        </Box>
        {(method === 'POST' || method === 'PATCH' || method === 'PUT') && (
          <TextField
            label="Request Body (JSON)"
            value={body}
            onChange={e => setBody(e.target.value)}
            multiline
            minRows={3}
            fullWidth
            sx={{ mb: 2 }}
          />
        )}
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
