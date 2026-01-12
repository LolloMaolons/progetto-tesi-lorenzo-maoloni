import { ApolloServer } from 'apollo-server';
import { gql } from 'apollo-server';
import fetch from 'node-fetch';
import depthLimit from 'graphql-depth-limit';
import { register, Counter, Histogram } from 'prom-client';
import winston from 'winston';
import http from 'http';

const REST_BASE = process.env.REST_BASE_URL || 'http://localhost:8080';
const LOW_STOCK_THRESHOLD = parseInt(process.env.LOW_STOCK_THRESHOLD || "25", 10);
const GRAPHQL_DEPTH_LIMIT = parseInt(process.env.GRAPHQL_DEPTH_LIMIT || "7", 10);
const INTROSPECTION_ENABLED = process.env.INTROSPECTION_ENABLED !== "false";
const RATE_LIMIT_PER_MIN = parseInt(process.env.RATE_LIMIT_PER_MIN || "100", 10);

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [new winston.transports.Console()],
});

const requestCounter = new Counter({
  name: 'graphql_requests_total',
  help: 'Total GraphQL requests',
  labelNames: ['operation', 'status'],
});

const requestDuration = new Histogram({
  name: 'graphql_request_duration_seconds',
  help: 'GraphQL request duration',
  labelNames: ['operation'],
});

const errorCounter = new Counter({
  name: 'graphql_errors_total',
  help: 'Total GraphQL errors',
  labelNames: ['operation'],
});

const rateLimitMap = new Map();

setInterval(() => {
  const now = Date.now();
  for (const [ip, data] of rateLimitMap.entries()) {
    if (now - data.windowStart > 60000) {
      rateLimitMap.delete(ip);
    }
  }
}, 30000);

function checkRateLimit(ip) {
  const now = Date.now();
  const data = rateLimitMap.get(ip);
  
  if (!data) {
    rateLimitMap.set(ip, { count: 1, windowStart: now });
    return true;
  }
  
  if (now - data.windowStart > 60000) {
    rateLimitMap.set(ip, { count: 1, windowStart: now });
    return true;
  }
  
  if (data.count >= RATE_LIMIT_PER_MIN) {
    return false;
  }
  
  data.count++;
  return true;
}

const typeDefs = gql`
  type Product {
    id: ID!
    name: String!
    price: Float!
    stock: Int!
    category: String
    description: String
    lowStock: Boolean!
    # Aggiunto per permettere query ricorsive (depth limit testing)
    recommendations(limit: Int = 3): [Product!]!
  }

  type Query {
    product(id: ID!): Product
    products(limit: Int, category: String): [Product!]!
    # Mantenuto per compatibilità backward, accessibile dalla root
    recommendations(id: ID!, limit: Int = 3): [Product!]!
  }
`;

const resolvers = {
  Product: {
    lowStock: (parent) => parent.stock <= LOW_STOCK_THRESHOLD,
    recommendations: async (parent, { limit }, context) => {
      const res = await fetch(`${REST_BASE}/products/${parent.id}/recommendations?limit=${limit}`);
      if (res.status !== 200) return [];
      return res.json();
    },
  },
  Query: {
    product: async (_, { id }, context) => {
      const res = await fetch(`${REST_BASE}/products/${id}`);
      if (res.status !== 200) return null;
      return res.json();
    },
    products: async (_, { limit, category }, context) => {
      const qs = new URLSearchParams();
      if (limit) qs.append("limit", limit);
      if (category) qs.append("category", category);
      const res = await fetch(`${REST_BASE}/products${qs.toString() ? "?" + qs.toString() : ""}`);
      return res.json();
    },
    recommendations: async (_, { id, limit }, context) => {
      const res = await fetch(`${REST_BASE}/products/${id}/recommendations?limit=${limit}`);
      if (res.status !== 200) return [];
      return res.json();
    },
  },
};

const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: INTROSPECTION_ENABLED,
  validationRules: [depthLimit(GRAPHQL_DEPTH_LIMIT)],
  context: ({ req }) => {
    const requestId = req.headers['x-request-id'] || `${Date.now()}`;
    const traceId = req.headers['x-trace-id'] || requestId;
    const ip = req.ip || req.connection.remoteAddress;

    if (!checkRateLimit(ip)) {
      throw new Error('Rate limit exceeded');
    }


    logger.info('GraphQL request', {
      requestId,
      traceId,
      ip,
      operation: req.body?.operationName,
    });

    return {
      requestId,
      traceId,
    };
  },
  plugins: [
    {
      async requestDidStart(requestContext) {
        const start = Date.now();
        const operation = requestContext.request.operationName || 'anonymous';

        return {
          async didEncounterErrors(ctx) {
            errorCounter.labels(operation).inc();
            logger.error('GraphQL error', {
              operation,
              errors: ctx.errors.map(e => e.message),
              requestId: ctx.context.requestId,
            });
          },
          async willSendResponse(ctx) {
            const duration = (Date.now() - start) / 1000;
            const status = ctx.errors ? 'error' : 'success';
            requestCounter.labels(operation, status).inc();
            requestDuration.labels(operation).observe(duration);
            logger.info('GraphQL response', {
              operation,
              status,
              duration_ms: Math.round(duration * 1000),
              requestId: ctx.context.requestId,
            });
          },
        };
      },
    },
  ],
});

const metricsServer = http.createServer(async (req, res) => {
  if (req.url === '/metrics') {
    res.setHeader('Content-Type', register.contentType);
    res.end(await register.metrics());
  } else {
    res.statusCode = 404;
    res.end('Not Found');
  }
});

metricsServer.listen(9090, () => {
  logger.info('Metrics server ready at http://localhost:9090/metrics');
});

server.listen({ port: 4000 }).then(({ url }) => {
  logger.info(`GraphQL server ready at ${url}`);
});