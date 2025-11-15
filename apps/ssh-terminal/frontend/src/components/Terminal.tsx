import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';

interface TerminalProps {
  websocket: WebSocket | null;
  onDisconnect?: () => void;
}

export const Terminal: React.FC<TerminalProps> = ({ websocket, onDisconnect }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm.js
    const xterm = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#0f172a',
        foreground: '#e2e8f0',
        cursor: '#8b5cf6',
        cursorAccent: '#1e293b',
        black: '#1e293b',
        red: '#ef4444',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#8b5cf6',
        cyan: '#06b6d4',
        white: '#e2e8f0',
        brightBlack: '#475569',
        brightRed: '#f87171',
        brightGreen: '#34d399',
        brightYellow: '#fbbf24',
        brightBlue: '#60a5fa',
        brightMagenta: '#a78bfa',
        brightCyan: '#22d3ee',
        brightWhite: '#f1f5f9',
      },
      allowProposedApi: true,
    });

    // Add addons
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    xterm.loadAddon(fitAddon);
    xterm.loadAddon(webLinksAddon);

    // Open terminal
    xterm.open(terminalRef.current);
    fitAddon.fit();

    // Store references
    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    // Welcome message
    xterm.writeln('\x1b[1;35m╔════════════════════════════════════════╗\x1b[0m');
    xterm.writeln('\x1b[1;35m║      SSH Web Terminal Connected        ║\x1b[0m');
    xterm.writeln('\x1b[1;35m╚════════════════════════════════════════╝\x1b[0m');
    xterm.writeln('');

    // Handle terminal resize
    const handleResize = () => {
      fitAddon.fit();
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
          type: 'resize',
          cols: xterm.cols,
          rows: xterm.rows
        }));
      }
    };

    window.addEventListener('resize', handleResize);

    // Handle terminal input
    const disposable = xterm.onData((data) => {
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
          type: 'input',
          data: data
        }));
      }
    });

    // Cleanup
    return () => {
      disposable.dispose();
      window.removeEventListener('resize', handleResize);
      xterm.dispose();
    };
  }, []);

  // Handle WebSocket messages
  useEffect(() => {
    if (!websocket || !xtermRef.current) return;

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);

        if (message.type === 'output' && xtermRef.current) {
          xtermRef.current.write(message.data);
        } else if (message.type === 'error' && xtermRef.current) {
          xtermRef.current.writeln(`\r\n\x1b[1;31m✖ Error: ${message.message}\x1b[0m\r\n`);
        } else if (message.type === 'close') {
          if (xtermRef.current) {
            xtermRef.current.writeln('\r\n\x1b[1;33m⚠ Connection closed\x1b[0m\r\n');
          }
          if (onDisconnect) {
            setTimeout(onDisconnect, 2000);
          }
        }
      } catch (error) {
        // Handle binary data (raw SSH output)
        if (typeof event.data === 'string' && xtermRef.current) {
          xtermRef.current.write(event.data);
        }
      }
    };

    const handleClose = () => {
      if (xtermRef.current) {
        xtermRef.current.writeln('\r\n\x1b[1;31m✖ WebSocket connection closed\x1b[0m\r\n');
      }
      if (onDisconnect) {
        setTimeout(onDisconnect, 2000);
      }
    };

    const handleError = () => {
      if (xtermRef.current) {
        xtermRef.current.writeln('\r\n\x1b[1;31m✖ WebSocket connection error\x1b[0m\r\n');
      }
    };

    websocket.addEventListener('message', handleMessage);
    websocket.addEventListener('close', handleClose);
    websocket.addEventListener('error', handleError);

    // Send initial resize
    if (websocket.readyState === WebSocket.OPEN && xtermRef.current) {
      websocket.send(JSON.stringify({
        type: 'resize',
        cols: xtermRef.current.cols,
        rows: xtermRef.current.rows
      }));
    }

    return () => {
      websocket.removeEventListener('message', handleMessage);
      websocket.removeEventListener('close', handleClose);
      websocket.removeEventListener('error', handleError);
    };
  }, [websocket, onDisconnect]);

  return (
    <div className="h-screen w-full bg-slate-950 flex flex-col">
      <div className="bg-slate-900/90 backdrop-blur-sm border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span className="text-slate-400 text-sm font-medium">SSH Terminal</span>
        </div>
        <button
          onClick={onDisconnect}
          className="text-slate-400 hover:text-red-400 transition-colors text-sm font-medium"
        >
          Disconnect
        </button>
      </div>
      <div
        ref={terminalRef}
        className="flex-1 overflow-hidden"
        style={{ minHeight: 0 }}
      />
    </div>
  );
};
