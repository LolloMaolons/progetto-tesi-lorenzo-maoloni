
import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, TextField, Button, Divider, IconButton, List, ListItem, ListItemButton, ListItemText, ListItemIcon, Tooltip } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import DescriptionIcon from '@mui/icons-material/Description';
import DeleteIcon from '@mui/icons-material/Delete';
import { request, gql } from 'graphql-request';
import { saveRequests, loadRequests } from './requestStore';

const DEFAULTS = [
  {
    name: 'All products (tutti campi)',
    query: `query {
      products {
        id
        name
        price
        stock
        category
        description
      }
    }`,
  },
  {
    name: 'Un prodotto (tutti campi)',
    query: `query {
      product(id: 1) {
        id
        name
        price
        stock
        category
        description
      }
    }`,
  },
  {
    name: 'Profondità 5 (valida)',
    query: `query {
      products {
        recommendations {
          recommendations {
            recommendations {
              recommendations {
                id
              }
            }
          }
        }
      }
    }`,
  },
  {
    name: 'Profondità 8 (bloccata)',
    query: `query {
      products {
        recommendations {
          recommendations {
            recommendations {
              recommendations {
                recommendations {
                  recommendations {
                    recommendations {
                      id
                    }
                  }
                }
              }
            }
          }
        }
      }
    }`,
  },
];

export default function ApiGraphQL() {
  const [queries, setQueries] = useState(() => loadRequests('graphql-queries', DEFAULTS));
  const [selected, setSelected] = useState(0);
  const [url, setUrl] = useState('http://localhost:4000/graphql');
  const [query, setQuery] = useState(queries[0].query);
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSave, setShowSave] = useState(false);

  useEffect(() => {
    setQuery(queries[selected].query);
    setShowSave(false);
  }, [selected, queries]);

  useEffect(() => {
    const isPreset = queries.some(q => q.query === query);
    setShowSave(!isPreset && query);
  }, [query, queries]);

  const handleSend = async () => {
    setLoading(true);
    setResponse('');
    try {
      const data = await request(url, gql`${query}`);
      setResponse(JSON.stringify(data, null, 2));
    } catch (err) {
      setResponse(err.response ? JSON.stringify(err.response, null, 2) : err.message);
    }
    setLoading(false);
  };

  const handleSelect = idx => {
    setSelected(idx);
  };

  const handleAdd = () => {
    setQuery('');
    setShowSave(false);
  };

  const handleSave = () => {
    const newQ = { name: `Custom Query ${queries.length + 1}`, query };
    const newList = [...queries, newQ];
    setQueries(newList);
    saveRequests('graphql-queries', newList);
    setSelected(newList.length - 1);
    setShowSave(false);
  };

  const handleDelete = idx => {
    if (idx < DEFAULTS.length) return;
    const newList = queries.filter((_, i) => i !== idx);
    setQueries(newList);
    saveRequests('graphql-queries', newList);
    setSelected(Math.max(0, idx - 1));
  };

  const handleResetDefaults = () => {
    setQueries(DEFAULTS);
    saveRequests('graphql-queries', DEFAULTS);
    setSelected(0);
    setQuery(DEFAULTS[0].query);
    setShowSave(false);
  };

  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      <Paper elevation={1} sx={{ minWidth: 260, maxWidth: 320, p: 1, mr: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, mt: 1, fontWeight: 700 }}>Queries</Typography>
        <List dense>
          {queries.map((q, i) => (
            <ListItem key={i} disablePadding
              secondaryAction={i >= DEFAULTS.length ? (
                <Tooltip title="Rimuovi query personalizzata">
                  <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(i)} size="small">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              ) : null}
            >
              <ListItemButton selected={selected === i} onClick={() => handleSelect(i)}>
                <ListItemIcon><DescriptionIcon color={selected === i ? 'primary' : 'action'} /></ListItemIcon>
                <ListItemText primary={q.name} secondary={q.query.slice(0, 40) + (q.query.length > 40 ? '...' : '')} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Button startIcon={<AddIcon />} onClick={handleAdd} variant="outlined" sx={{ mt: 1 }}>Nuova query</Button>
        <Button color="error" variant="outlined" sx={{ mt: 1 }} onClick={handleResetDefaults}>
          Ripristina queries di default
        </Button>
      </Paper>
      <Paper elevation={2} sx={{ flex: 1, p: 3, minWidth: 0 }}>
        <Typography variant="h6" gutterBottom>GraphQL API Tester</Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField label="Endpoint" value={url} onChange={e => setUrl(e.target.value)} fullWidth />
          <IconButton color="primary" onClick={handleSend} disabled={loading} size="large">
            <SendIcon />
          </IconButton>
        </Box>
        <TextField
          label="GraphQL Query"
          value={query}
          onChange={e => setQuery(e.target.value)}
          multiline
          minRows={5}
          fullWidth
          sx={{ mb: 2 }}
        />
        {showSave && (
          <Button startIcon={<SaveIcon />} onClick={handleSave} color="primary" variant="contained" sx={{ mb: 2 }}>
            Salva query
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
