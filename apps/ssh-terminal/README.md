# SSH Web Terminal

A modern, browser-based SSH terminal built with React, TypeScript, and xterm.js.

## Features

- 🚀 Beautiful, modern UI with Tailwind CSS v4
- 🔐 Secure SSH connections via WebSocket
- 💻 Full terminal emulation with xterm.js
- 🎨 Animated UI components with Framer Motion
- 📱 Responsive design
- 🔒 Session management and rate limiting
- ⚡ Real-time bidirectional communication

## Tech Stack

### Frontend
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS v4
- xterm.js (terminal emulator)
- Framer Motion (animations)
- Shadcn/ui components
- WebSocket client

### Backend
- Node.js + Express
- TypeScript
- WebSocket (ws library)
- SSH2 (SSH client)
- Express Session
- Rate limiting

## Project Structure

```
ssh-web-terminal/
├── frontend/          # React frontend application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── lib/          # Utilities
│   │   └── App.tsx       # Main app component
│   └── package.json
├── backend/           # Node.js backend server
│   ├── src/
│   │   ├── server.ts     # Express + WebSocket server
│   │   ├── ssh-manager.ts # SSH connection handler
│   │   └── session.ts    # Session management
│   └── package.json
└── package.json       # Root package.json
```

## Installation

1. Install dependencies:
```bash
npm install
cd frontend && npm install
cd ../backend && npm install
```

2. Configure environment variables:

Create `backend/.env`:
```env
PORT=3000
SESSION_SECRET=your-secure-secret-here
NODE_ENV=development
```

## Development

Start both frontend and backend in development mode:

```bash
npm run dev
```

Or start them separately:

```bash
# Frontend (runs on http://localhost:5173)
npm run dev:frontend

# Backend (runs on http://localhost:3000)
npm run dev:backend
```

## Security Features

- ✅ Input validation on frontend and backend
- ✅ Rate limiting (5 connection attempts per minute per IP)
- ✅ Session-based connection tracking
- ✅ Secure WebSocket communication
- ✅ No password storage or logging
- ✅ Automatic disconnect on idle timeout
- ✅ Error-first design pattern

## Usage

1. Open the application in your browser (http://localhost:5173)
2. Enter your SSH connection details:
   - Hostname or IP address
   - Port (default: 22)
   - Username
   - Password
3. Click "Connect to Server"
4. Interact with the remote server through the terminal

## Building for Production

```bash
npm run build
```

This will build both frontend and backend for production deployment.

## License

MIT

## Security Notice

⚠️ This application handles SSH credentials. Always use HTTPS/WSS in production and never expose the backend directly to the internet without proper authentication and authorization mechanisms.
