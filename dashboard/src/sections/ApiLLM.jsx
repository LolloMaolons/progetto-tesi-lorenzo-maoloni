import React, { useState } from 'react';
import { Box, Paper, Typography, TextField, Button, Divider, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import axios from 'axios';

export default function ApiLLM() {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [mcpResult, setMcpResult] = useState('');

  const handleSend = async () => {
    setLoading(true);
    setResponse('');
    setMcpResult('');
    try {
      const res = await axios.post('http://localhost:5000/llm-invoke', { prompt });
      setResponse(res.data.result);

      // Prova a fare il parsing della risposta come JSON
      let parsed;
      try {
        parsed = typeof res.data.result === 'string' ? JSON.parse(res.data.result) : res.data.result;
      } catch (e) {
        parsed = null;
      }

      // Se è un JSON-RPC valido, esegui la chiamata MCP
      if (parsed && parsed.method && (parsed.params !== undefined || parsed.params === null)) {
        try {
          // Endpoint corretto MCP
          const mcpRes = await axios.post('http://localhost:5000/rpc', parsed);
          setMcpResult(JSON.stringify(mcpRes.data, null, 2));
        } catch (mcpErr) {
          setMcpResult(mcpErr.response ? JSON.stringify(mcpErr.response.data, null, 2) : mcpErr.message);
        }
      }
    } catch (err) {
      setResponse(err.response ? JSON.stringify(err.response.data, null, 2) : err.message);
    }
    setLoading(false);
  };

  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      <Paper elevation={2} sx={{ flex: 1, p: 3, minWidth: 0 }}>
        <Typography variant="h6" gutterBottom>LLM API Tester</Typography>
        <TextField
          label="Prompt"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          multiline
          minRows={3}
          fullWidth
          sx={{ mb: 2 }}
        />
        <Button
          startIcon={<SendIcon />}
          onClick={handleSend}
          color="primary"
          variant="contained"
          disabled={loading || !prompt}
          sx={{ mb: 2 }}
        >
          Invia
        </Button>
        {loading && <CircularProgress size={24} sx={{ ml: 2 }} />}
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" color="text.secondary">Risposta LLM</Typography>
        <Box sx={{ bgcolor: '#f5f5f5', borderRadius: 1, p: 2, minHeight: 80, fontFamily: 'monospace', fontSize: 15, whiteSpace: 'pre-wrap' }}>
          {response}
        </Box>
        {mcpResult && <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" color="text.secondary">Risultato MCP</Typography>
          <Box sx={{ bgcolor: '#e3f2fd', borderRadius: 1, p: 2, minHeight: 80, fontFamily: 'monospace', fontSize: 15, whiteSpace: 'pre-wrap' }}>
            {mcpResult}
          </Box>
        </>}
      </Paper>
    </Box>
  );
}
