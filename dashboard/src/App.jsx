import React from 'react';
import { ThemeProvider, createTheme, CssBaseline, Box, AppBar, Toolbar, Typography, Tabs, Tab } from '@mui/material';
import ApiRest from './sections/ApiRest';
import ApiGraphQL from './sections/ApiGraphQL';
import ApiWebSocket from './sections/ApiWebSocket';
import ApiJsonRpc from './sections/ApiJsonRpc';
import { WebSocketProvider } from './sections/WebSocketContext';
import { ApiOutlined, CodeOutlined, WebOutlined, DataObjectOutlined, SmartToyOutlined } from '@mui/icons-material';
import ApiLLM from './sections/ApiLLM';

const theme = createTheme({
  palette: {
    mode: 'light',
    background: { default: '#f7f9fb' },
    primary: { main: '#1976d2' },
    secondary: { main: '#424242' },
  },
  typography: {
    fontFamily: 'Inter, Roboto, Arial, sans-serif',
    h6: { fontWeight: 700 },
  },
});

const sections = [
  { label: 'REST', icon: <ApiOutlined />, component: <ApiRest /> },
  { label: 'GraphQL', icon: <CodeOutlined />, component: <ApiGraphQL /> },
  { label: 'WebSocket', icon: <WebOutlined />, component: <ApiWebSocket /> },
  { label: 'JSON-RPC', icon: <DataObjectOutlined />, component: <ApiJsonRpc /> },
  { label: 'LLM', icon: <SmartToyOutlined />, component: <ApiLLM /> },
];

export default function App() {
  const [tab, setTab] = React.useState(0);

  return (
    <ThemeProvider theme={theme}>
      <WebSocketProvider>
        <CssBaseline />
        <AppBar position="static" color="default" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Toolbar>
            <Typography variant="h6" color="primary" sx={{ flexGrow: 1 }}>
              API Dashboard
            </Typography>
          </Toolbar>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v)}
            indicatorColor="primary"
            textColor="primary"
            centered
          >
            {sections.map((s, i) => (
              <Tab key={s.label} icon={s.icon} label={s.label} />
            ))}
          </Tabs>
        </AppBar>
        <Box sx={{ p: 3, maxWidth: 1100, mx: 'auto', minHeight: '80vh' }}>
          {sections[tab].component}
        </Box>
      </WebSocketProvider>
    </ThemeProvider>
  );
}
