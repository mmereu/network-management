import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import { createServer } from 'http';
import session from 'express-session';
import rateLimit from 'express-rate-limit';
import cors from 'cors';
import dotenv from 'dotenv';
import { SSHManager } from './ssh-manager.js';

dotenv.config();

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

// WebSocket CORS handling
wss.on('headers', (headers, req) => {
  const origin = req.headers.origin;

  // Allow localhost on any port in development
  if (!origin || origin.match(/^http:\/\/localhost:\d+$/)) {
    headers.push('Access-Control-Allow-Origin: ' + (origin || '*'));
    headers.push('Access-Control-Allow-Credentials: true');
  }
});

// Middleware
app.use(cors({
  origin: (origin, callback) => {
    // Allow localhost on any port in development
    if (!origin || origin.match(/^http:\/\/localhost:\d+$/)) {
      callback(null, true);
    } else {
      callback(null, origin === (process.env.FRONTEND_URL || 'http://localhost:5173'));
    }
  },
  credentials: true
}));

app.use(express.json());

// Session configuration
const sessionMiddleware = session({
  secret: process.env.SESSION_SECRET || 'change-this-in-production',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
});

app.use(sessionMiddleware);

// Rate limiting
const connectionLimiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000'),
  max: parseInt(process.env.MAX_CONNECTION_ATTEMPTS || '5'),
  message: 'Too many connection attempts, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});

// Map to store SSH connections by WebSocket
const sshConnections = new Map<WebSocket, SSHManager>();

// WebSocket connection handler
wss.on('connection', (ws: WebSocket, req) => {
  console.log('New WebSocket connection');

  // Apply rate limiting
  const ip = req.socket.remoteAddress || 'unknown';
  console.log(`Connection from: ${ip}`);

  ws.on('message', async (data: Buffer) => {
    try {
      const message = JSON.parse(data.toString());

      // Handle SSH connection request
      if (message.type === 'connect') {
        // Validate credentials
        if (!message.hostname || !message.port || !message.username || !message.password) {
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Missing required connection parameters'
          }));
          return;
        }

        // Validate hostname (IP or domain)
        const hostnameRegex = /^(\d{1,3}\.){3}\d{1,3}$|^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
        if (!hostnameRegex.test(message.hostname)) {
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Invalid hostname or IP address'
          }));
          return;
        }

        // Validate port
        const port = parseInt(message.port);
        if (isNaN(port) || port < 1 || port > 65535) {
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Invalid port number'
          }));
          return;
        }

        // Create SSH connection
        const sshManager = new SSHManager({
          host: message.hostname,
          port: port,
          username: message.username,
          password: message.password,
          timeout: parseInt(process.env.SSH_TIMEOUT || '30000'),
          keepaliveInterval: parseInt(process.env.SSH_KEEPALIVE_INTERVAL || '10000')
        });

        // Store SSH connection
        sshConnections.set(ws, sshManager);

        // Connect to SSH server
        try {
          await sshManager.connect();

          // Send success message
          ws.send(JSON.stringify({
            type: 'connected',
            message: 'SSH connection established'
          }));

          // Handle SSH data
          sshManager.on('data', (data: string) => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({
                type: 'output',
                data: data
              }));
            }
          });

          // Handle SSH errors
          sshManager.on('error', (error: Error) => {
            console.error('SSH Error:', error);
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({
                type: 'error',
                message: error.message
              }));
            }
          });

          // Handle SSH close
          sshManager.on('close', () => {
            console.log('SSH connection closed');
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({
                type: 'close',
                message: 'SSH connection closed'
              }));
              ws.close();
            }
            sshConnections.delete(ws);
          });

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'SSH connection failed';
          console.error('SSH Connection Error:', errorMessage);

          ws.send(JSON.stringify({
            type: 'error',
            message: errorMessage
          }));

          sshConnections.delete(ws);
        }
      }
      // Handle terminal input
      else if (message.type === 'input') {
        const sshManager = sshConnections.get(ws);
        if (sshManager) {
          sshManager.write(message.data);
        }
      }
      // Handle terminal resize
      else if (message.type === 'resize') {
        const sshManager = sshConnections.get(ws);
        if (sshManager && message.cols && message.rows) {
          sshManager.resize(message.cols, message.rows);
        }
      }

    } catch (error) {
      console.error('WebSocket message error:', error);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Invalid message format'
      }));
    }
  });

  ws.on('close', () => {
    console.log('WebSocket connection closed');
    const sshManager = sshConnections.get(ws);
    if (sshManager) {
      sshManager.disconnect();
      sshConnections.delete(ws);
    }
  });

  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
    const sshManager = sshConnections.get(ws);
    if (sshManager) {
      sshManager.disconnect();
      sshConnections.delete(ws);
    }
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    activeConnections: sshConnections.size
  });
});

// Error handling middleware (error-first design)
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Express Error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// Start server
const PORT = parseInt(process.env.PORT || '3000');

server.listen(PORT, () => {
  console.log(`🚀 SSH Web Terminal server running on port ${PORT}`);
  console.log(`📡 WebSocket endpoint: ws://localhost:${PORT}/ws`);
  console.log(`🏥 Health check: http://localhost:${PORT}/health`);
  console.log(`🔒 Environment: ${process.env.NODE_ENV || 'development'}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  sshConnections.forEach((sshManager) => {
    sshManager.disconnect();
  });
  sshConnections.clear();
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
