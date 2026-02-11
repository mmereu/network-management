import { Client, ClientChannel } from 'ssh2';
import { EventEmitter } from 'events';

interface SSHConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  timeout?: number;
  keepaliveInterval?: number;
}

export class SSHManager extends EventEmitter {
  private client: Client;
  private stream: ClientChannel | null = null;
  private config: SSHConfig;
  private connected: boolean = false;

  constructor(config: SSHConfig) {
    super();
    this.client = new Client();
    this.config = config;
    this.setupClientHandlers();
  }

  private setupClientHandlers(): void {
    this.client.on('ready', () => {
      console.log('SSH Client :: ready');

      // Request shell
      this.client.shell(
        {
          term: 'xterm-256color',
          cols: 80,
          rows: 24
        },
        (err, stream) => {
          if (err) {
            console.error('SSH Shell Error:', err);
            this.emit('error', err);
            this.disconnect();
            return;
          }

          this.stream = stream;
          this.connected = true;

          // Handle stream data
          stream.on('data', (data: Buffer) => {
            this.emit('data', data.toString('utf-8'));
          });

          // Handle stream close
          stream.on('close', () => {
            console.log('SSH Stream :: close');
            this.connected = false;
            this.emit('close');
            this.disconnect();
          });

          // Handle stream errors
          stream.stderr.on('data', (data: Buffer) => {
            this.emit('data', data.toString('utf-8'));
          });
        }
      );
    });

    this.client.on('error', (err: Error) => {
      console.error('SSH Client Error:', err);
      this.connected = false;
      this.emit('error', err);
    });

    this.client.on('close', () => {
      console.log('SSH Client :: close');
      this.connected = false;
      this.emit('close');
    });

    this.client.on('end', () => {
      console.log('SSH Client :: end');
      this.connected = false;
    });
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Set timeout for connection
      const timeout = setTimeout(() => {
        this.disconnect();
        reject(new Error('SSH connection timeout'));
      }, this.config.timeout || 30000);

      this.client.once('ready', () => {
        clearTimeout(timeout);
        resolve();
      });

      this.client.once('error', (err: Error) => {
        clearTimeout(timeout);
        reject(err);
      });

      // Connect to SSH server
      try {
        this.client.connect({
          host: this.config.host,
          port: this.config.port,
          username: this.config.username,
          password: this.config.password,
          readyTimeout: this.config.timeout || 30000,
          keepaliveInterval: this.config.keepaliveInterval || 10000,
          keepaliveCountMax: 3,
          // Security options - include legacy algorithms for older network devices
          algorithms: {
            kex: [
              'diffie-hellman-group-exchange-sha256',
              'diffie-hellman-group-exchange-sha1',
              'diffie-hellman-group14-sha256',
              'diffie-hellman-group14-sha1',
              'diffie-hellman-group1-sha1', // Legacy for old Huawei devices
              'ecdh-sha2-nistp256',
              'ecdh-sha2-nistp384',
              'ecdh-sha2-nistp521'
            ],
            cipher: [
              'aes128-ctr',
              'aes192-ctr',
              'aes256-ctr',
              'aes128-gcm',
              'aes128-gcm@openssh.com',
              'aes256-gcm',
              'aes256-gcm@openssh.com',
              'aes128-cbc', // Legacy
              'aes192-cbc', // Legacy
              'aes256-cbc', // Legacy
              '3des-cbc'    // Legacy for very old devices
            ],
            serverHostKey: [
              'ssh-rsa',
              'ssh-dss',
              'ecdsa-sha2-nistp256',
              'ecdsa-sha2-nistp384',
              'ecdsa-sha2-nistp521',
              'ssh-ed25519',
              'rsa-sha2-256', // Modern
              'rsa-sha2-512'  // Modern
            ],
            hmac: [
              'hmac-sha2-256',
              'hmac-sha2-512',
              'hmac-sha1', // Legacy
              'hmac-md5'   // Legacy for very old devices
            ]
          }
        });
      } catch (error) {
        clearTimeout(timeout);
        reject(error);
      }
    });
  }

  write(data: string): void {
    if (this.stream && this.connected) {
      this.stream.write(data);
    } else {
      console.warn('Attempted to write to disconnected SSH stream');
    }
  }

  resize(cols: number, rows: number): void {
    if (this.stream && this.connected) {
      this.stream.setWindow(rows, cols, 480, 640);
    }
  }

  disconnect(): void {
    if (this.stream) {
      this.stream.end();
      this.stream = null;
    }

    if (this.connected) {
      this.client.end();
      this.connected = false;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }
}
