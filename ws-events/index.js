import WebSocket, { WebSocketServer } from 'ws';
import { createClient } from 'redis';
import winston from 'winston';
import { Counter } from 'prom-client';
import http from 'http';

const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379/0";
const MAX_PAYLOAD = parseInt(process.env.WS_MAX_PAYLOAD || "1048576", 10);
const ALLOWED_ORIGINS = (process.env.WS_ALLOWED_ORIGINS || "*").split(",");
const MESSAGE_RATE_LIMIT = parseInt(process.env.WS_MESSAGE_RATE_LIMIT || "20", 10);
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [new winston.transports.Console()],
});

const wsConnections = new Counter({
  name: 'ws_connections_total',
  help: 'Total WebSocket connections',
});

const wsMessages = new Counter({
  name: 'ws_messages_total',
  help: 'Total WebSocket messages sent',
  labelNames: ['type'],
});

const wsErrors = new Counter({
  name: 'ws_errors_total',
  help: 'Total WebSocket errors',
  labelNames: ['type'],
});

const wss = new WebSocketServer({ 
  port: 7070,
  maxPayload: MAX_PAYLOAD,
  verifyClient: (info, cb) => {
    const origin = info.origin || info.req.headers.origin;
    
    if (ALLOWED_ORIGINS[0] !== "*" && !ALLOWED_ORIGINS.includes(origin)) {
      logger.warn('Connection rejected: disallowed origin', { origin });
      wsErrors.labels('origin_rejected').inc();
      cb(false, 403, 'Origin not allowed');
      return;
    }

    cb(true);
  }
});

const connectionRateLimits = new Map();

setInterval(() => {
  const now = Date.now();
  for (const [connId, limits] of connectionRateLimits.entries()) {
    if (now - limits.lastAccess > 120000) {
      connectionRateLimits.delete(connId);
    }
  }
}, 60000);

function checkMessageRateLimit(connectionId) {
  const now = Date.now();
  const limits = connectionRateLimits.get(connectionId) || { count: 0, windowStart: now, lastAccess: now };
  
  limits.lastAccess = now;
  
  if (now - limits.windowStart > 1000) {
    limits.count = 1;
    limits.windowStart = now;
    connectionRateLimits.set(connectionId, limits);
    return true;
  } else {
    limits.count++;
    if (limits.count > MESSAGE_RATE_LIMIT) {
      return false;
    }
    connectionRateLimits.set(connectionId, limits);
    return true;
  }
}


(async () => {
  const sub = createClient({ url: REDIS_URL });

  sub.on('error', (err) => {
    logger.error('Redis client error', { error: err.message });
  });
  sub.on('end', () => {
    logger.error('Redis connection closed');
  });
  sub.on('reconnecting', () => {
    logger.warn('Redis client reconnecting...');
  });

  try {
    await sub.connect();
  } catch (err) {
    logger.error('Failed to connect to Redis', { error: err.message });
    process.exit(1);
  }

  await sub.subscribe('events', (message) => {
    const traceId = `evt-${Date.now()}`;
    let eventData;

    try {
      eventData = JSON.parse(message);
    } catch (err) {
      logger.error('Invalid event message', { error: err.message, traceId });
      return;
    }

    logger.info('Broadcasting event', {
      traceId,
      eventType: eventData.type,
      clientCount: wss.clients.size,
    });

    wss.clients.forEach(c => {
      if (c.readyState === WebSocket.OPEN) {
        c.send(message);
        wsMessages.labels(eventData.type || 'unknown').inc();
      }
    });
  });

  logger.info("WebSocket server listening on 7070, subscribed to 'events'");
})();

wss.on('connection', (ws, req) => {
  const connectionId = `conn-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
  const user = req.user || { role: 'anonymous' };
  
  wsConnections.inc()
  ws.connectionId = connectionId;
  connectionRateLimits.set(connectionId, { count: 0, windowStart: Date.now(), lastAccess: Date.now() });
  
  logger.info('WebSocket connection established', {
    connectionId,
    user: user.sub || 'anonymous',
    role: user.role,
  });

  ws.send(JSON.stringify({ 
    type: "welcome", 
    connectionId,
    ts: Date.now() 
  }));

  ws.on('message', (data) => {
    if (!checkMessageRateLimit(connectionId)) {
      logger.warn('Message rate limit exceeded', { connectionId });
      wsErrors.labels('rate_limit').inc();
      ws.send(JSON.stringify({ type: 'error', message: 'Rate limit exceeded' }));
      return;
    }

    logger.info('Message received from client', {
      connectionId,
      size: data.length,
    });
  });

  ws.on('error', (err) => {
    logger.error('WebSocket error', {
      connectionId,
      error: err.message,
    });
    wsErrors.labels('connection_error').inc();
  });

  ws.on('close', () => {
    logger.info('WebSocket connection closed', { connectionId });
    connectionRateLimits.delete(connectionId);
  });
});
