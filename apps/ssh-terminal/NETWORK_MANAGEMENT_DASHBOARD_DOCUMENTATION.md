# Network Management Dashboard - Documentazione Completa

**Server**: 172.24.1.33
**Versione Sistema**: 1.0
**Data Analisi**: 2025-11-15

---

## 📋 Indice

1. [Architettura Generale](#architettura-generale)
2. [Servizi Attivi](#servizi-attivi)
3. [Dettaglio Servizi](#dettaglio-servizi)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Database](#database)
6. [Deployment e Processi](#deployment-e-processi)
7. [Note Manutenzione](#note-manutenzione)

---

## 🏗️ Architettura Generale

### Stack Tecnologico

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT BROWSER                            │
│              http://172.24.1.33/index.html                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┴────────────────┐
       │                                │
       ▼                                ▼
┌─────────────────┐           ┌──────────────────┐
│  Apache/Nginx   │           │   Node.js        │
│   Port 80       │           │   Port 8443      │
│  (Static HTML)  │           │  (SSH Terminal)  │
└────────┬────────┘           └──────────────────┘
         │
    ┌────┴────────────────────┐
    │                         │
    ▼                         ▼
┌──────────────┐      ┌──────────────┐
│  Flask API   │      │  Flask API   │
│  Port 5001   │      │  Port 5002   │
│ (ConfigSw)   │      │ (PortMapper) │
└──────┬───────┘      └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  ▼
          ┌───────────────┐
          │  SQLite DB    │
          │monitoring.db  │
          └───────────────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
    ┌─────────┐      ┌──────────┐
    │PostgreSQL│      │  SNMP    │
    │NetTrack  │      │ Huawei   │
    │  DB      │      │ Switches │
    └──────────┘      └──────────┘
```

### Componenti Principali

| Componente | Tecnologia | Porta | Path | Stato |
|-----------|-----------|-------|------|-------|
| **Homepage Dashboard** | HTML/CSS | 80 | `/var/www/html/` | ✅ Attivo |
| **ConfigSwitch Backend** | Python Flask | 5001 | `/home/mmereu/` | ✅ Attivo |
| **Port Mapper Backend** | Python Flask | 5002 | `/home/mmereu/huawei_vlan/` | ✅ Attivo |
| **Migration Service** | Python Flask | 9999 | `/var/backup/old_projects/huawei-switch-migration/` | ✅ Attivo |
| **SSH Terminal** | Node.js + Express | 8443 | `/home/mmereu/ssh-web-terminal/` | ✅ Attivo |
| **Monitoring App** | Python Flask | (integrato) | `/var/www/html/` | ✅ Attivo |
| **Discovery Dashboard** | Python Flask | (integrato) | `/home/mmereu/nettrack/` | ✅ Attivo |

---

## 🌐 Servizi Attivi

### Tabella Riepilogativa

| # | Servizio | URL | Porta | Tecnologia | Funzione |
|---|---------|-----|-------|-----------|----------|
| 1 | **Migrazione Switch Multi-Vendor** | `http://172.24.1.33:9999` | 9999 | Flask + Jinja2 | Conversione config HP/Huawei → Huawei stack |
| 2 | **Configurazione Switch Huawei (React)** | `http://172.24.1.33:8443/config-switch` | 8443 | Node.js + React | Gestione automatica config switch via SSH |
| 3 | **Huawei Switch Port Mapper** | `http://172.24.1.33:5002` | 5002 | Flask + React | Mappatura porte/VLAN via SNMP |
| 4 | **Monitoring Dashboard** | `http://172.24.1.33/monitor_process.html` | 80 | Flask + HTML | Monitoraggio processi config real-time |
| 5 | **Network Discovery** | `http://172.24.1.33/discovery.html` | 80 | Flask + PostgreSQL | Scansione SNMP dispositivi (gsmon) |
| 6 | **Config Switch HTML Classic** | `http://172.24.1.33/huawei-test.html` | 80 | HTML + Flask API | Versione HTML config switch |
| 7 | **SSH Terminal** | `http://172.24.1.33:8443/` | 8443 | Node.js + WebSocket | Terminal SSH web-based |

---

## 📦 Dettaglio Servizi

### 1️⃣ Migrazione Switch Multi-Vendor

**Descrizione**: Strumento completo per migrazione configurazioni da switch HP/Huawei legacy verso stack Huawei moderni.

**Tecnologie**:
- Backend: Python Flask
- Frontend: Jinja2 Templates
- SSH: Paramiko
- Parsing: Regex multi-vendor

**Path Progetto**: `/var/backup/old_projects/huawei-switch-migration/`

**Moduli Principali**:
```
huawei-switch-migration/
├── run.py                          # Entry point (port 9999)
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── routes.py                   # API endpoints
│   ├── ssh_manager.py              # SSH connection handling
│   ├── config_parser.py            # Parser configurazioni
│   ├── interface_translator.py    # Traduzione interfacce
│   ├── template_generator.py      # Generatore config Huawei
│   └── universal_interface_parser.py  # Parser multi-vendor
└── templates/
    └── index.html                  # Web UI
```

**API Endpoints**:
- `POST /extract_config` - Estrazione config da switch source
- `POST /generate_config` - Generazione config switch destination
- `POST /generate_config_complete` - Config completa con VLAN
- `POST /download_config` - Download file config generato

**Workflow Operativo**:
```
1. User input: IP switch source, credenziali, tipo (24/48 port)
2. SSH connection → extract config (show interface brief)
3. Parsing config per interfaccia (VLAN, trunk/access, etc.)
4. Traduzione naming HP/Huawei → Huawei stack
5. Generazione template config Huawei
6. Download file .txt pronto per apply
```

**Caratteristiche**:
- ✅ Supporto multi-vendor (HP, Huawei legacy)
- ✅ Gestione stack switch (unit numbering)
- ✅ Filtering uplink ports (>24 o >48)
- ✅ Template completi con VLAN, IP management, password
- ✅ Fallback automatico se `show interface brief` fallisce

---

### 2️⃣ Configurazione Switch Huawei

**Descrizione**: Applicazione per gestione automatica configurazioni switch Huawei via SSH con monitoraggio real-time.

**Tecnologie**:
- Backend: Python Flask (`app_huawei_final.py`)
- SSH: Paramiko con shell interattiva
- Database: SQLite (`monitoring.db`)
- Cache: Flask-Caching (5min TTL per VLAN)
- SNMP: pysnmp per discovery
- Frontend: HTML statico + JavaScript (API calls)

**Path Backend**: `/home/mmereu/app_huawei_final.py`

**Funzionalità Core**:

1. **Configurazione SSH Automatica**:
   - Esecuzione comandi batch su switch Huawei
   - Gestione login interattivo (Username/Password prompt)
   - Supporto multi-switch parallelo
   - Tracking progress per singolo switch

2. **SNMP Discovery**:
   - Scansione subnet per dispositivi Huawei
   - Identificazione via sysDescr OID
   - Raccolta hostname, uptime, location

3. **Monitoring Sistema**:
   - Tracking processi configurazione attivi
   - Database SQLite per persistenza stato
   - Statistiche success rate, timing, errori
   - Allarmi dispositivi down

**Database Schema** (`monitoring.db`):
```sql
-- Processi configurazione
CREATE TABLE processes (
    id INTEGER PRIMARY KEY,
    status TEXT,                 -- running/completed/failed
    progress INTEGER,            -- 0-100
    devices_configured INTEGER,
    devices_total INTEGER,
    errors INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Log dettagliati per processo
CREATE TABLE process_logs (
    id INTEGER PRIMARY KEY,
    process_id INTEGER,
    timestamp TEXT,
    type TEXT,                   -- info/warning/error/success
    message TEXT
);

-- Dispositivi monitorati
CREATE TABLE monitored_devices (
    id INTEGER PRIMARY KEY,
    ip TEXT UNIQUE,
    hostname TEXT,
    device_type TEXT,
    status TEXT,                 -- online/offline/warning
    last_check TIMESTAMP,
    created_at TIMESTAMP
);

-- Allarmi
CREATE TABLE alarms (
    id INTEGER PRIMARY KEY,
    device_id INTEGER,
    alarm_type TEXT,
    message TEXT,
    severity TEXT,               -- critical/warning/info
    timestamp TIMESTAMP,
    resolved INTEGER DEFAULT 0
);
```

**Classe `ConfigProcess`**:
```python
class ConfigProcess:
    process_id: str              # UUID processo
    status: str                  # running/completed/failed
    progress: int                # 0-100
    total_hosts: int
    completed_hosts: int
    failed_hosts: int
    logs: list                   # Log entries
    start_time: datetime
    stop_requested: bool
    switch_results: list         # Tracking per singolo switch

    Methods:
    - add_log(message, level)
    - init_switch(ip, name)
    - update_switch_status(ip, status, error_msg)
```

**API Endpoints** (Port 5001):

**Configurazione**:
- `POST /api/execute` - Esegue comandi SSH su switch
  - Body: `{hostname, username, password, commands[], process_id}`
  - Response: `{success, process_id, message}`

**Monitoraggio Processi**:
- `GET /api/status` - Status tutti processi attivi
- `GET /api/status/<process_id>` - Dettagli singolo processo
- `POST /api/stop/<process_id>` - Arresta processo
- `GET /api/processes` - Lista completa processi
- `GET /api/health` - Health check servizio

**SNMP Discovery**:
- `POST /api/discovery` - Avvia scansione SNMP subnet
  - Body: `{network, community}`
  - Response: `{process_id, message}`
- `GET /api/discovery/results/<process_id>` - Risultati discovery
- `GET /api/discovery/export/<process_id>` - Export CSV

**Device Monitoring**:
- `POST /api/monitoring/add` - Aggiungi dispositivo a monitoring
- `GET /api/monitoring/status/<ip>` - Status singolo device
- `GET /api/monitoring/list` - Lista tutti device monitorati
- `DELETE /api/monitoring/remove/<device_id>` - Rimuovi device

**Allarmi**:
- `GET /api/alarms/list` - Lista allarmi attivi
- `GET /api/alarms/count` - Count allarmi per severity
- `POST /api/alarms/resolve/<alarm_id>` - Risolvi allarme

**Statistiche**:
- `GET /api/statistics` - Statistiche generali sistema

**Funzione SSH `execute_single_command`**:
```python
def execute_single_command(hostname, username, password, command, process):
    """
    Esegue singolo comando SSH su Huawei switch

    Features:
    - Auto-detection Username/Password prompts
    - Interactive shell (Paramiko invoke_shell)
    - Buffer cleaning post-login
    - Timeout gestiti (2s login, 3s command, 20 loop iterations)
    - Cleanup output (rimozione prompt, escape codes)
    """
    # 1. SSH connect (standard auth + fallback interactive)
    # 2. Shell interactive
    # 3. Login handling (detect prompts, send credentials)
    # 4. Buffer flush
    # 5. Send command
    # 6. Read output (with timeout)
    # 7. Cleanup and return
```

**Helper `clean_snmp_value`**:
```python
def clean_snmp_value(value):
    """
    Pulisce valori SNMP grezzi
    Examples:
        'STRING: "10_L2_Rack0_25"' -> '10_L2_Rack0_25'
        'Timeticks: (3821656195) 442 days' -> '442 days'
        'INTEGER: 123' -> '123'
    """
```

---

### 3️⃣ Huawei Switch Port Mapper

**Descrizione**: Applicazione per mappatura visuale porte switch Huawei via SNMP con dettagli VLAN, status, trunk/access.

**Tecnologie**:
- Backend: Python Flask (`app_switch_mapper.py`)
- SNMP: Custom client ottimizzato con query parallele
- Frontend: React (servito da Flask static)
- Parallel Processing: ThreadPoolExecutor (max 4 workers)

**Path Progetto**: `/home/mmereu/huawei_vlan/`

**Architettura**:
```
huawei_vlan/
├── app_switch_mapper.py          # Flask app principale
├── snmp_client.py                # SNMP base client
├── snmp_client_enhanced.py       # Port status/stack detection
├── snmp_optimized.py             # Optimized parallel queries
└── frontend/dist/                # React build (static)
```

**Moduli SNMP**:

1. **SNMPClient** (`snmp_client.py`):
   - Base SNMP operations (GET/WALK/GETNEXT)
   - Bridge port to IfIndex mapping
   - VLAN membership retrieval

2. **Enhanced Functions** (`snmp_client_enhanced.py`):
   - `get_port_status()` - Operational status porte (up/down)
   - `detect_stack()` - Rilevamento switch stack
   - `get_port_count()` - Count porte disponibili

3. **OptimizedSNMPClient** (`snmp_optimized.py`):
   - `get_switch_data_optimized()` - Query parallele VLAN + porte
   - Batch SNMP walks
   - Performance: 30s → <10s per switch completo

**API Endpoints** (Port 5002):

- `POST /api/switch/map` - Mappa completa switch
  - Body: `{switch_ip, community}`
  - Response: Struttura completa porte + VLAN

- `POST /api/discover` - Discovery dispositivi subnet
  - Body: `{network, community}`

- `GET /api/health` - Health check

**Response Structure `/api/switch/map`**:
```json
{
  "switch_ip": "172.24.1.10",
  "switch_name": "10_L2_Rack0_25",
  "query_time": 8.45,
  "ports": [
    {
      "port_number": 1,
      "interface_name": "GigabitEthernet0/0/1",
      "pvid": 10,
      "tagged_vlans": [1, 10, 20],
      "is_trunk": false,
      "is_up": true,
      "oper_status": "up"
    },
    ...
  ],
  "vlans": [
    {
      "vlan_id": 10,
      "vlan_name": "DATA",
      "member_ports": [1, 2, 3, 4]
    },
    ...
  ],
  "stack_info": {
    "is_stack": false,
    "members": []
  }
}
```

**Performance Optimization**:
- Parallel SNMP queries (ThreadPoolExecutor)
- Timeout 30s per query batch
- Error handling per-port (fail gracefully)
- Warning logging per debugging

**Workflow Operativo**:
```
1. User input: switch_ip, community (default: gsmon)
2. Parallel SNMP queries (4 workers):
   - Switch data (VLAN + port membership)
   - Port operational status
   - Stack detection
   - Port count
3. Bridge-port to IfIndex mapping
4. Merge data (port + status + VLAN)
5. Identify trunk ports (PVID=1/999/4094 + Gig interface)
6. Return JSON completo
```

---

### 4️⃣ Monitoring Dashboard

**Descrizione**: Dashboard real-time per monitoraggio processi configurazione switch con log streaming.

**Tecnologie**:
- Backend: Python Flask (`monitor_process_app.py`)
- Database: SQLite (stesso `monitoring.db` usato da ConfigSwitch)
- Frontend: HTML + JavaScript (polling ogni 2s)

**Path**: `/var/www/html/monitor_process_app.py`

**API Endpoints**:

- `GET /api/latest-process` - Trova ultimo processo attivo
  - Response: `{processId}`

- `GET /api/status/<process_id>` - Status processo + log
  - Response:
    ```json
    {
      "status": "running",
      "progress": 75,
      "stats": {
        "devicesConfigured": 15,
        "devicesTotal": 20,
        "errors": 2,
        "successRate": 75.0
      },
      "log": [
        {"time": "10:30:15", "type": "info", "msg": "Connected to 172.24.1.10"},
        {"time": "10:30:18", "type": "success", "msg": "Config applied"}
      ]
    }
    ```

- `POST /api/stop/<process_id>` - Arresta processo

- `POST /api/test-process` - Crea processo test per debugging

**Frontend** (`monitor_process.html`):
- Auto-discovery ultimo processo attivo
- Polling status ogni 2 secondi
- Progress bar animata
- Color-coded logs (info/success/error/warning)
- Real-time statistics (success rate, timing)

**Integrazione**: Condivide database `monitoring.db` con ConfigSwitch backend (app_huawei_final.py), quindi mostra processi creati da entrambi servizi.

---

### 5️⃣ Network Discovery

**Descrizione**: Sistema discovery SNMP per rilevamento automatico dispositivi Huawei nella rete con dashboard PostgreSQL.

**Tecnologie**:
- Backend: Python Flask (`dashboard_app.py`)
- Database: PostgreSQL (`nettrack`)
- SNMP: Community `gsmon`
- Frontend: HTML templates (Jinja2)

**Path**: `/home/mmereu/nettrack/`

**Database PostgreSQL**:

Schema `nettrack`:
```sql
-- Discovery cycles
CREATE TABLE discovery_cycles (
    cycle_id INTEGER PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    successful_switches INTEGER,
    failed_switches INTEGER,
    total_mac_entries INTEGER
);

-- MAC address table
CREATE TABLE mac_address_table (
    id SERIAL PRIMARY KEY,
    switch_ip TEXT,
    port_index INTEGER,
    mac_address TEXT,
    vlan_id INTEGER,
    discovery_timestamp TIMESTAMP
);

-- LLDP neighbors
CREATE TABLE neighbor_discovery (
    id SERIAL PRIMARY KEY,
    local_switch_ip TEXT,
    local_port TEXT,
    neighbor_ip TEXT,
    neighbor_hostname TEXT,
    status TEXT  -- active/inactive
);

-- Feature flags (configurazione runtime)
CREATE TABLE feature_flags (
    flag_name TEXT PRIMARY KEY,
    flag_value BOOLEAN
);

-- Audit MAC changes
CREATE TABLE mac_discovery_audit (
    id SERIAL PRIMARY KEY,
    mac_address TEXT,
    old_port TEXT,
    new_port TEXT,
    discovery_timestamp TIMESTAMP
);
```

**API Endpoints**:

- `GET /` - Dashboard HTML principale

- `GET /api/summary` - Statistiche generali
  - Latest cycle info
  - Total MACs/LLDP neighbors
  - Feature flags status
  - Recent MAC changes (last hour)

- `GET /api/switches` - Statistiche per-switch

- `GET /api/cycles` - Storia discovery cycles

**Response `/api/summary`**:
```json
{
  "latest_cycle": {
    "cycle_number": 1234,
    "start_time": "2025-11-15T10:00:00",
    "end_time": "2025-11-15T10:15:00",
    "duration_seconds": 900,
    "switches_discovered": 45,
    "switches_failed": 2,
    "total_mac_entries": 2341
  },
  "total_macs": 23450,
  "total_lldp": 89,
  "feature_flags": {
    "auto_discovery": true,
    "mac_tracking": true
  },
  "recent_changes": 15
}
```

**Processo Discovery** (esterno, scheduler-based):
1. Scansione subnet SNMP community `gsmon`
2. Identificazione switch Huawei (sysDescr)
3. Raccolta MAC table (dot1dTpFdbTable)
4. LLDP neighbor discovery
5. Insert/update PostgreSQL
6. Audit tracking MAC movements

**Dashboard Features**:
- Real-time cycle progress
- Per-switch statistics
- MAC address search
- LLDP topology visualization
- Historical trends

---

### 6️⃣ Config Switch HTML Classic

**Descrizione**: Versione HTML classica (legacy) interfaccia configurazione switch, usa stesso backend API ConfigSwitch (port 5001).

**Path**: `/var/www/html/huawei-test.html`

**Tecnologie**:
- Frontend: HTML puro + JavaScript vanilla
- Backend: Stesso Flask API port 5001 (app_huawei_final.py)

**Features**:
- Form input switch (IP, user, password)
- Input comandi manuale
- Chiamate AJAX a `/api/execute`
- Display log risultati

**Differenze vs React**:
- No build process
- No dependencies frontend
- Stessa funzionalità core
- UI più semplice/legacy

**Uso**: Fallback quando React app non disponibile o per utenti che preferiscono UI minimale.

---

### 7️⃣ SSH Terminal

**Descrizione**: Terminal SSH web-based con WebSocket real-time per accesso remoto dispositivi di rete.

**Tecnologie**:
- Backend: Node.js + Express + TypeScript
- WebSocket: `ws` library
- SSH: `ssh2` library (SSH client Node.js)
- Frontend: React + Vite + xterm.js
- Session: express-session
- Security: Rate limiting, CORS

**Path Progetto**: `/home/mmereu/ssh-web-terminal/`

**Architettura**:
```
ssh-web-terminal/
├── backend/
│   ├── src/
│   │   ├── server.ts              # Main WebSocket server
│   │   └── ssh-manager.ts         # SSH connection management
│   ├── dist/                      # Compiled JavaScript
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # React main component
│   │   ├── SSHTerminal.tsx        # Terminal component (xterm.js)
│   │   └── api/websocket.ts       # WebSocket client
│   ├── dist/                      # Build React
│   └── package.json
└── .env                           # Environment config
```

**Backend Server** (`server.ts`):

```typescript
// Main components
const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

// Middleware
- CORS (localhost development + production)
- express-session (24h TTL)
- Rate limiting (5 connections/min per IP)

// WebSocket handlers
wss.on('connection', (ws, req) => {
  // Message types:
  - 'connect': SSH connection request
  - 'input': Send data to SSH
  - 'resize': Terminal resize
  - 'disconnect': Close SSH
});

// SSH connection tracking
const sshConnections = new Map<WebSocket, SSHConnection>();
```

**SSHManager** (`ssh-manager.ts`):

```typescript
class SSHManager {
  private client: Client;  // ssh2 Client
  private stream: ClientChannel;

  async connect(config: SSHConfig): Promise<void> {
    // SSH connection with authentication
    // Shell spawn
    // Data streaming to WebSocket
  }

  write(data: string): void {
    // Send input to SSH shell
  }

  resize(cols: number, rows: number): void {
    // Terminal resize
  }

  disconnect(): void {
    // Cleanup connection
  }
}
```

**Frontend Terminal** (`SSHTerminal.tsx`):

```typescript
// xterm.js terminal instance
const terminal = new Terminal({
  cursorBlink: true,
  theme: { background: '#1e1e1e' }
});

// WebSocket connection
const ws = new WebSocket('ws://172.24.1.33:8443/ws');

// Event handlers
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'output') {
    terminal.write(msg.data);
  }
};

terminal.onData((data) => {
  ws.send(JSON.stringify({ type: 'input', data }));
});
```

**WebSocket Message Protocol**:

Client → Server:
```json
// Connect
{
  "type": "connect",
  "hostname": "172.24.1.10",
  "port": 22,
  "username": "admin",
  "password": "******"
}

// Input
{
  "type": "input",
  "data": "show interface brief\n"
}

// Resize
{
  "type": "resize",
  "cols": 80,
  "rows": 24
}

// Disconnect
{
  "type": "disconnect"
}
```

Server → Client:
```json
// Output
{
  "type": "output",
  "data": "<GigabitEthernet0/0/1 ... >"
}

// Error
{
  "type": "error",
  "message": "Authentication failed"
}

// Connected
{
  "type": "connected",
  "message": "SSH connection established"
}
```

**Security Features**:
- Rate limiting (5 conn attempts/min)
- Session management (24h expiry)
- CORS restricted to configured origins
- Environment-based secrets (.env)
- Input validation per WebSocket messages

**Environment Variables** (`.env`):
```bash
PORT=8443
SESSION_SECRET=<random-secret>
FRONTEND_URL=http://localhost:5173
RATE_LIMIT_WINDOW_MS=60000
MAX_CONNECTION_ATTEMPTS=5
NODE_ENV=production
```

**Deployment**:
```bash
# Backend build
cd backend && npm run build

# Frontend build
cd frontend && npm run build

# Start server (systemd service)
node backend/dist/server.js
```

**Process**:
- PID 48533
- Command: `node /home/mmereu/ssh-web-terminal/backend/dist/server.js`
- Port: 8443
- Working dir: `/home/mmereu/ssh-web-terminal`

---

## 🔌 API Endpoints Reference

### ConfigSwitch API (Port 5001)

#### Configurazione Switch

**POST /api/execute**
```json
Request:
{
  "hostname": "172.24.1.10",
  "username": "admin",
  "password": "******",
  "commands": ["display interface brief", "display vlan"],
  "process_id": "optional-uuid"
}

Response:
{
  "success": true,
  "process_id": "abc123-...",
  "message": "Configuration started"
}
```

#### Monitoring

**GET /api/status/<process_id>**
```json
Response:
{
  "process_id": "abc123-...",
  "status": "running",
  "progress": 75,
  "total_hosts": 20,
  "completed_hosts": 15,
  "failed_hosts": 2,
  "start_time": "2025-11-15T10:00:00",
  "logs": [
    {"timestamp": "10:00:15", "level": "info", "message": "Connected to 172.24.1.10"},
    {"timestamp": "10:00:18", "level": "success", "message": "Config applied"}
  ],
  "switch_results": [
    {
      "switch_ip": "172.24.1.10",
      "switch_name": "SW-CORE-01",
      "status": "success",
      "execution_time": 12.5,
      "error_message": null
    }
  ]
}
```

**POST /api/stop/<process_id>**
```json
Response:
{
  "success": true,
  "message": "Stop requested"
}
```

#### Discovery

**POST /api/discovery**
```json
Request:
{
  "network": "172.24.1.0/24",
  "community": "gsmon"
}

Response:
{
  "success": true,
  "process_id": "discovery-xyz",
  "message": "Discovery started"
}
```

**GET /api/discovery/results/<process_id>**
```json
Response:
{
  "devices": [
    {
      "ip": "172.24.1.10",
      "hostname": "SW-CORE-01",
      "uptime": "45 days, 12:30:00",
      "location": "Rack 1"
    }
  ]
}
```

#### Device Monitoring

**POST /api/monitoring/add**
```json
Request:
{
  "ip": "172.24.1.10",
  "hostname": "SW-CORE-01",
  "device_type": "switch",
  "check_interval": 300
}

Response:
{
  "success": true,
  "device_id": 123
}
```

**GET /api/monitoring/list**
```json
Response:
{
  "devices": [
    {
      "id": 123,
      "ip": "172.24.1.10",
      "hostname": "SW-CORE-01",
      "status": "online",
      "last_check": "2025-11-15T10:30:00"
    }
  ]
}
```

#### Allarmi

**GET /api/alarms/list**
```json
Response:
{
  "alarms": [
    {
      "id": 1,
      "device_id": 123,
      "alarm_type": "device_down",
      "message": "Device 172.24.1.10 not responding",
      "severity": "critical",
      "timestamp": "2025-11-15T10:00:00",
      "resolved": 0
    }
  ]
}
```

---

### Port Mapper API (Port 5002)

**POST /api/switch/map**
```json
Request:
{
  "switch_ip": "172.24.1.10",
  "community": "gsmon"
}

Response:
{
  "switch_ip": "172.24.1.10",
  "switch_name": "10_L2_Rack0_25",
  "query_time": 8.45,
  "ports": [
    {
      "port_number": 1,
      "interface_name": "GigabitEthernet0/0/1",
      "pvid": 10,
      "tagged_vlans": [1, 10, 20],
      "is_trunk": false,
      "is_up": true,
      "oper_status": "up"
    }
  ],
  "vlans": [
    {
      "vlan_id": 10,
      "vlan_name": "DATA",
      "member_ports": [1, 2, 3, 4]
    }
  ],
  "stack_info": {
    "is_stack": false,
    "members": []
  }
}
```

---

### Migration API (Port 9999)

**POST /extract_config**
```json
Request:
{
  "ip": "172.24.1.50",
  "username": "admin",
  "password": "******",
  "unit_number": 1,
  "switch_type": "24"  // or "48"
}

Response:
{
  "success": true,
  "interfaces": [
    {
      "interface": "GigabitEthernet1/0/1",
      "description": "User Port",
      "pvid": 10,
      "tagged_vlans": [],
      "mode": "access"
    }
  ],
  "count": 24
}
```

**POST /generate_config_complete**
```json
Request:
{
  "interfaces": [...],  // From extract_config
  "switch_name": "NEW-SW-01",
  "switch_ip": "172.24.1.60",
  "switch_gateway": "172.24.1.1",
  "admin_password": "NewPass123"
}

Response:
{
  "success": true,
  "config": "# Huawei Switch Configuration\nsysname NEW-SW-01\n...",
  "filename": "NEW-SW-01_complete_config.txt"
}
```

---

### Monitoring Dashboard API (Port 80)

**GET /api/latest-process**
```json
Response:
{
  "processId": 123
}
```

**GET /api/status/<process_id>**
```json
Response:
{
  "status": "running",
  "progress": 75,
  "stats": {
    "devicesConfigured": 15,
    "devicesTotal": 20,
    "errors": 2,
    "successRate": 75.0
  },
  "log": [
    {"time": "10:30:15", "type": "info", "msg": "Connected to 172.24.1.10"}
  ]
}
```

---

### Discovery Dashboard API (Port 80)

**GET /api/summary**
```json
Response:
{
  "latest_cycle": {
    "cycle_number": 1234,
    "start_time": "2025-11-15T10:00:00",
    "switches_discovered": 45,
    "total_mac_entries": 2341
  },
  "total_macs": 23450,
  "total_lldp": 89
}
```

---

## 💾 Database

### SQLite: monitoring.db

**Path**: `/var/www/html/monitoring.db`

**Utilizzato da**:
- ConfigSwitch Backend (app_huawei_final.py) - Write
- Monitoring Dashboard (monitor_process_app.py) - Read

**Schema**:
```sql
-- Processi configurazione
CREATE TABLE processes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT,                    -- running/completed/failed/stopped
    progress INTEGER,               -- 0-100
    devices_configured INTEGER,
    devices_total INTEGER,
    errors INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Log eventi processo
CREATE TABLE process_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id INTEGER,
    timestamp TEXT,
    type TEXT,                      -- info/success/error/warning
    message TEXT,
    FOREIGN KEY (process_id) REFERENCES processes(id)
);

-- Dispositivi sotto monitoring
CREATE TABLE monitored_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT UNIQUE NOT NULL,
    hostname TEXT,
    device_type TEXT,               -- switch/router/firewall
    status TEXT,                    -- online/offline/warning
    last_check TIMESTAMP,
    check_interval INTEGER,         -- Secondi tra check
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sistema allarmi
CREATE TABLE alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER,
    alarm_type TEXT,                -- device_down/high_cpu/interface_down
    message TEXT,
    severity TEXT,                  -- critical/warning/info
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved INTEGER DEFAULT 0,     -- 0=attivo, 1=risolto
    resolved_at TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES monitored_devices(id)
);
```

**Indici**:
```sql
CREATE INDEX idx_process_status ON processes(status, started_at);
CREATE INDEX idx_process_logs_pid ON process_logs(process_id);
CREATE INDEX idx_monitored_devices_ip ON monitored_devices(ip);
CREATE INDEX idx_alarms_device_resolved ON alarms(device_id, resolved);
```

---

### PostgreSQL: nettrack

**Host**: 172.24.1.33
**Database**: nettrack
**User**: nettrack_app
**Port**: 5432 (default)

**Utilizzato da**:
- Discovery Dashboard (dashboard_app.py)
- Discovery Background Process (scheduler esterno)

**Schema**:
```sql
-- Cicli discovery SNMP
CREATE TABLE discovery_cycles (
    cycle_id SERIAL PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    successful_switches INTEGER DEFAULT 0,
    failed_switches INTEGER DEFAULT 0,
    total_mac_entries INTEGER DEFAULT 0,
    status TEXT                     -- running/completed/failed
);

-- MAC address table aggregata
CREATE TABLE mac_address_table (
    id SERIAL PRIMARY KEY,
    switch_ip INET NOT NULL,
    port_index INTEGER,
    interface_name TEXT,
    mac_address MACADDR NOT NULL,
    vlan_id INTEGER,
    discovery_timestamp TIMESTAMP NOT NULL,
    cycle_id INTEGER,
    FOREIGN KEY (cycle_id) REFERENCES discovery_cycles(cycle_id)
);

-- LLDP topology
CREATE TABLE neighbor_discovery (
    id SERIAL PRIMARY KEY,
    local_switch_ip INET NOT NULL,
    local_port TEXT,
    neighbor_ip INET,
    neighbor_hostname TEXT,
    neighbor_port TEXT,
    status TEXT DEFAULT 'active',   -- active/inactive
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    cycle_id INTEGER,
    FOREIGN KEY (cycle_id) REFERENCES discovery_cycles(cycle_id)
);

-- Feature flags runtime
CREATE TABLE feature_flags (
    flag_name TEXT PRIMARY KEY,
    flag_value BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit MAC movements
CREATE TABLE mac_discovery_audit (
    id SERIAL PRIMARY KEY,
    mac_address MACADDR NOT NULL,
    old_switch_ip INET,
    old_port TEXT,
    new_switch_ip INET,
    new_port TEXT,
    discovery_timestamp TIMESTAMP NOT NULL,
    cycle_id INTEGER,
    FOREIGN KEY (cycle_id) REFERENCES discovery_cycles(cycle_id)
);

-- Switch inventory
CREATE TABLE switch_inventory (
    id SERIAL PRIMARY KEY,
    switch_ip INET UNIQUE NOT NULL,
    hostname TEXT,
    model TEXT,
    serial_number TEXT,
    software_version TEXT,
    location TEXT,
    uptime_seconds BIGINT,
    last_discovery TIMESTAMP
);
```

**Indici Performance**:
```sql
CREATE INDEX idx_mac_switch_vlan ON mac_address_table(switch_ip, vlan_id);
CREATE INDEX idx_mac_address ON mac_address_table(mac_address);
CREATE INDEX idx_mac_timestamp ON mac_address_table(discovery_timestamp DESC);
CREATE INDEX idx_neighbor_local ON neighbor_discovery(local_switch_ip);
CREATE INDEX idx_audit_mac ON mac_discovery_audit(mac_address);
```

---

## 🚀 Deployment e Processi

### Processi Attivi (verificato ps + netstat)

| Processo | PID | User | Command | Porta | Status |
|---------|-----|------|---------|-------|--------|
| **Apache/Nginx** | - | www-data | `/usr/sbin/apache2` | 80 | ✅ Running |
| **ConfigSwitch** | - | mmereu | `python3 app_huawei_final.py` | 5001 | ✅ Running |
| **Port Mapper** | - | mmereu | `python3 app_switch_mapper.py` | 5002 | ✅ Running |
| **Migration** | - | mmereu | `python3 run.py` | 9999 | ✅ Running |
| **SSH Terminal** | 48533 | mmereu | `node backend/dist/server.js` | 8443 | ✅ Running |
| **Monitoring** | - | www-data | `python3 monitor_process_app.py` | - | ✅ Running |
| **Discovery** | - | mmereu | `python3 dashboard_app.py` | - | ✅ Running |

### Systemd Services (ipotizzato)

**ConfigSwitch**:
```ini
[Unit]
Description=Huawei Switch Configuration Service
After=network.target

[Service]
Type=simple
User=mmereu
WorkingDirectory=/home/mmereu
ExecStart=/usr/bin/python3 app_huawei_final.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Port Mapper**:
```ini
[Unit]
Description=Huawei Switch Port Mapper
After=network.target

[Service]
Type=simple
User=mmereu
WorkingDirectory=/home/mmereu/huawei_vlan
ExecStart=/usr/bin/python3 app_switch_mapper.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**SSH Terminal**:
```ini
[Unit]
Description=SSH Web Terminal
After=network.target

[Service]
Type=simple
User=mmereu
WorkingDirectory=/home/mmereu/ssh-web-terminal
ExecStart=/usr/bin/node backend/dist/server.js
Restart=always
RestartSec=10
Environment="NODE_ENV=production"

[Install]
WantedBy=multi-user.target
```

**Migration**:
```ini
[Unit]
Description=Switch Migration Service
After=network.target

[Service]
Type=simple
User=mmereu
WorkingDirectory=/var/backup/old_projects/huawei-switch-migration
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### File System Paths

```
/var/www/html/
├── index.html                      # Dashboard homepage
├── monitor_process.html            # Monitoring UI
├── monitor_process_app.py          # Monitoring backend
├── discovery.html                  # Discovery UI
├── huawei-test.html               # Config Switch HTML classic
└── monitoring.db                   # SQLite database

/home/mmereu/
├── app_huawei_final.py            # ConfigSwitch backend
├── huawei_vlan/
│   ├── app_switch_mapper.py       # Port Mapper backend
│   ├── snmp_client.py
│   ├── snmp_client_enhanced.py
│   └── snmp_optimized.py
├── nettrack/
│   └── dashboard_app.py           # Discovery backend
└── ssh-web-terminal/
    ├── backend/
    │   └── dist/server.js         # SSH Terminal backend
    └── frontend/dist/             # React build

/var/backup/old_projects/
└── huawei-switch-migration/
    ├── run.py                     # Migration entry point
    └── app/
        ├── routes.py
        ├── ssh_manager.py
        ├── config_parser.py
        └── ...
```

---

## 🔧 Note Manutenzione

### Backup Database

**SQLite (monitoring.db)**:
```bash
# Backup
sqlite3 /var/www/html/monitoring.db ".backup /backup/monitoring_$(date +%Y%m%d).db"

# Restore
cp /backup/monitoring_20251115.db /var/www/html/monitoring.db
chown www-data:www-data /var/www/html/monitoring.db
```

**PostgreSQL (nettrack)**:
```bash
# Backup
pg_dump -h 172.24.1.33 -U nettrack_app -d nettrack > /backup/nettrack_$(date +%Y%m%d).sql

# Restore
psql -h 172.24.1.33 -U nettrack_app -d nettrack < /backup/nettrack_20251115.sql
```

### Log Rotation

Configurare logrotate per gestire log crescenti:

```bash
# /etc/logrotate.d/network-management
/home/mmereu/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 mmereu mmereu
    postrotate
        systemctl reload configswitch
        systemctl reload portmapper
    endscript
}
```

### Health Checks

**Script Monitoraggio**:
```bash
#!/bin/bash
# /home/mmereu/scripts/health_check.sh

SERVICES=(
    "5001:ConfigSwitch"
    "5002:PortMapper"
    "9999:Migration"
    "8443:SSHTerminal"
)

for service in "${SERVICES[@]}"; do
    port=$(echo $service | cut -d: -f1)
    name=$(echo $service | cut -d: -f2)

    if netstat -tuln | grep -q ":$port "; then
        echo "✅ $name (port $port) - OK"
    else
        echo "❌ $name (port $port) - DOWN"
        # Alert/restart logic
    fi
done
```

### Performance Tuning

**Flask Workers** (Gunicorn):
```bash
# ConfigSwitch con Gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app_huawei_final:app

# Port Mapper con Gunicorn
gunicorn -w 2 -b 0.0.0.0:5002 app_switch_mapper:app
```

**Database Optimization**:
```sql
-- SQLite vacuum periodico
VACUUM;
ANALYZE;

-- PostgreSQL vacuum
VACUUM ANALYZE mac_address_table;
VACUUM ANALYZE neighbor_discovery;
```

### Troubleshooting

**Common Issues**:

1. **SSH Timeout su ConfigSwitch**:
   - Controllare firewall tra server e switch
   - Verificare credenziali switch
   - Aumentare timeout in `execute_single_command()` (default 30s)

2. **SNMP No Response Port Mapper**:
   - Verificare community string (default: `gsmon`)
   - Controllare ACL SNMP su switch
   - Test manuale: `snmpwalk -v2c -c gsmon 172.24.1.10 1.3.6.1.2.1.1.5.0`

3. **WebSocket Disconnect SSH Terminal**:
   - Controllare nginx/apache reverse proxy config
   - Verificare keep-alive timeout
   - Check browser console per errori CORS

4. **Database Lock SQLite**:
   - Troppi writer simultanei
   - Valutare migrazione a PostgreSQL per load alto
   - Usare WAL mode: `PRAGMA journal_mode=WAL;`

### Update Procedures

**Backend Update**:
```bash
# Backup database
sqlite3 /var/www/html/monitoring.db ".backup /backup/pre_update.db"

# Stop services
systemctl stop configswitch portmapper migration

# Update code
cd /home/mmereu
git pull origin main  # (se versioned)

# Restart services
systemctl start configswitch portmapper migration

# Verify
curl http://172.24.1.33:5001/api/health
curl http://172.24.1.33:5002/api/health
```

**Frontend Update (SSH Terminal)**:
```bash
cd /home/mmereu/ssh-web-terminal/frontend
npm run build
systemctl restart sshterminal
```

### Security Recommendations

1. **Credential Storage**:
   - NON salvare password in chiaro nei database
   - Usare environment variables per secrets
   - Considerare vault (HashiCorp Vault/Ansible Vault)

2. **API Rate Limiting**:
   - Implementare rate limiting su Flask (Flask-Limiter)
   - SSH Terminal già ha rate limiting (5 conn/min)

3. **HTTPS**:
   - Configurare reverse proxy nginx con SSL/TLS
   - Let's Encrypt per certificati
   - Redirect HTTP → HTTPS

4. **Firewall**:
   - Limitare accesso porte Flask solo da LAN
   - UFW rules:
     ```bash
     ufw allow from 172.24.1.0/24 to any port 5001
     ufw allow from 172.24.1.0/24 to any port 5002
     ufw allow from 172.24.1.0/24 to any port 8443
     ufw allow from 172.24.1.0/24 to any port 9999
     ```

---

## 📊 Diagrammi Architettura

### Flusso Configurazione Switch

```
┌─────────────┐
│   User UI   │
│ (Browser)   │
└──────┬──────┘
       │ 1. POST /api/execute
       │    {hosts, commands}
       ▼
┌─────────────────────┐
│  ConfigSwitch API   │
│   (Port 5001)       │
└──────┬──────────────┘
       │ 2. Create ConfigProcess
       │    UUID, status=running
       ▼
┌─────────────────────┐
│ Process Manager     │
│ (active_processes)  │
└──────┬──────────────┘
       │ 3. For each switch:
       │    - SSH connect (Paramiko)
       │    - Login interactive
       │    - Execute commands
       │    - Capture output
       ▼
┌─────────────────────┐
│   Huawei Switch     │
│  (172.24.1.x)       │
└──────┬──────────────┘
       │ 4. Command output
       ▼
┌─────────────────────┐
│  SQLite DB          │
│  monitoring.db      │
│  - Insert process   │
│  - Insert logs      │
└──────┬──────────────┘
       │ 5. Polling status
       ▼
┌─────────────────────┐
│ Monitoring UI       │
│ (monitor_process)   │
│ - Progress bar      │
│ - Live logs         │
└─────────────────────┘
```

### Flusso Port Mapping

```
┌─────────────┐
│   User UI   │
└──────┬──────┘
       │ 1. POST /api/switch/map
       │    {switch_ip, community}
       ▼
┌─────────────────────┐
│  Port Mapper API    │
│   (Port 5002)       │
└──────┬──────────────┘
       │ 2. Parallel SNMP queries (ThreadPool)
       │
       ├─► SNMP Walk: VLANs + Port membership
       ├─► SNMP Get: Port operational status
       ├─► SNMP Get: Stack detection
       └─► SNMP Get: Port count
       │
       ▼
┌─────────────────────┐
│   Huawei Switch     │
│  SNMP Agent         │
│  Community: gsmon   │
└──────┬──────────────┘
       │ 3. SNMP responses
       ▼
┌─────────────────────┐
│  Data Processing    │
│  - Merge port data  │
│  - Identify trunks  │
│  - Map bridge→ifIndex
└──────┬──────────────┘
       │ 4. JSON response
       ▼
┌─────────────────────┐
│   React UI          │
│  - Visual port map  │
│  - VLAN table       │
│  - Color-coded      │
└─────────────────────┘
```

### Flusso Migration

```
┌─────────────┐
│   User UI   │
└──────┬──────┘
       │ 1. POST /extract_config
       │    {old_switch_ip, creds, type}
       ▼
┌─────────────────────┐
│  Migration API      │
│   (Port 9999)       │
└──────┬──────────────┘
       │ 2. SSH connect old switch
       ▼
┌─────────────────────┐
│  HP/Huawei Legacy   │
│  Old Switch         │
└──────┬──────────────┘
       │ 3. show interface brief
       │    show interface GigX/X/X
       ▼
┌─────────────────────┐
│  Config Parser      │
│  - Parse output     │
│  - Extract VLANs    │
│  - Trunk detection  │
└──────┬──────────────┘
       │ 4. Interface list JSON
       ▼
┌─────────────────────┐
│  User Review        │
│  (Web UI)           │
└──────┬──────────────┘
       │ 5. POST /generate_config_complete
       │    {interfaces, switch_name, IP, etc}
       ▼
┌─────────────────────┐
│  Template Generator │
│  - Translate names  │
│  - Generate VLAN    │
│  - System config    │
└──────┬──────────────┘
       │ 6. Huawei config file
       ▼
┌─────────────────────┐
│  Download .txt      │
│  Ready for paste    │
│  into new switch    │
└─────────────────────┘
```

### Flusso SSH Terminal

```
┌─────────────┐
│  Browser    │
│  React UI   │
└──────┬──────┘
       │ 1. WebSocket connect
       │    ws://172.24.1.33:8443/ws
       ▼
┌─────────────────────┐
│  Node.js Server     │
│  Express + ws       │
└──────┬──────────────┘
       │ 2. WS message: 'connect'
       │    {hostname, port, user, pass}
       ▼
┌─────────────────────┐
│  SSHManager         │
│  (ssh2 library)     │
└──────┬──────────────┘
       │ 3. SSH connect
       │    Spawn shell
       ▼
┌─────────────────────┐
│  Target Device      │
│  (Switch/Router)    │
└──────┬──────────────┘
       │ 4. Shell data stream
       ▼
┌─────────────────────┐
│  WebSocket          │
│  Message: 'output'  │
└──────┬──────────────┘
       │ 5. Display in xterm.js
       ▼
┌─────────────────────┐
│  User sees shell    │
│  + sends input      │
└─────────────────────┘
```

---

## 📝 Workflow Operativi

### Scenario 1: Configurare 20 Switch

1. **Preparazione**:
   - File CSV con lista switch (IP, user, password)
   - Comandi da eseguire preparati

2. **Esecuzione**:
   - Accesso ConfigSwitch UI (http://172.24.1.33/huawei-test.html o port 8443)
   - Upload CSV o input manuale
   - POST `/api/execute` con lista switch + comandi
   - Ottenere `process_id`

3. **Monitoraggio**:
   - Aprire Monitoring Dashboard (http://172.24.1.33/monitor_process.html)
   - Auto-detection ultimo processo o input `process_id`
   - Seguire progress bar + log real-time
   - Attendere completamento

4. **Verifica**:
   - Controllare success rate
   - Analizzare errori per switch failed
   - Download log completo

### Scenario 2: Mapping Porte Switch

1. **Input**:
   - IP switch target
   - Community SNMP (default: gsmon)

2. **Esecuzione**:
   - Accesso Port Mapper (http://172.24.1.33:5002)
   - POST `/api/switch/map`
   - Wait ~8-10 secondi

3. **Visualizzazione**:
   - Mappa visuale porte (grid layout)
   - Tabella VLAN con port members
   - Status up/down per porta
   - Trunk ports highlighted

4. **Export**:
   - Download JSON completo
   - Screenshot per documentazione

### Scenario 3: Migrazione Switch

1. **Fase 1 - Extraction**:
   - Accesso Migration UI (http://172.24.1.33:9999)
   - Input switch source (HP/Huawei old)
   - POST `/extract_config`
   - Review JSON interfacce estratte

2. **Fase 2 - Customization**:
   - Modificare VLAN naming se necessario
   - Aggiungere descrizioni porte
   - Configurare IP management nuovo switch

3. **Fase 3 - Generation**:
   - POST `/generate_config_complete`
   - Download file `.txt`

4. **Fase 4 - Apply**:
   - Usare SSH Terminal (http://172.24.1.33:8443)
   - Connect a nuovo switch Huawei
   - Paste config (system-view)
   - Save config

### Scenario 4: Discovery Rete

1. **Trigger**:
   - Accesso ConfigSwitch API
   - POST `/api/discovery` con subnet (e.g., 172.24.1.0/24)

2. **Processo**:
   - SNMP walk su subnet
   - Identificazione dispositivi Huawei
   - Raccolta hostname, uptime, location

3. **Risultati**:
   - GET `/api/discovery/results/<process_id>`
   - Lista dispositivi trovati
   - Export CSV per inventory

4. **Dashboard**:
   - Accesso Discovery Dashboard (http://172.24.1.33/discovery.html)
   - Visualizzazione statistiche ciclo
   - MAC table aggregata
   - LLDP topology

---

## 🎯 Use Cases Pratici

### Use Case 1: VLAN Configuration su 50 Switch

**Obiettivo**: Aggiungere VLAN 100 "VOIP" su 50 switch

**Steps**:
1. Preparare comando Huawei:
   ```
   system-view
   vlan 100
   description VOIP
   quit
   save
   ```

2. Creare file CSV switch:
   ```csv
   ip,username,password
   172.24.1.10,admin,Pass123
   172.24.1.11,admin,Pass123
   ...
   ```

3. API call:
   ```bash
   curl -X POST http://172.24.1.33:5001/api/execute \
     -H "Content-Type: application/json" \
     -d '{
       "hosts": ["172.24.1.10", "172.24.1.11", ...],
       "credentials": {"username": "admin", "password": "Pass123"},
       "commands": ["system-view", "vlan 100", "description VOIP", "quit", "save"]
     }'
   ```

4. Monitoring:
   - http://172.24.1.33/monitor_process.html
   - Follow progress
   - Check success rate

**Risultato atteso**: VLAN 100 creata su 50 switch in ~10 minuti

---

### Use Case 2: Audit Trunk Ports

**Obiettivo**: Identificare tutte le porte trunk nella rete

**Steps**:
1. Accesso Port Mapper UI

2. Scansione per ogni switch:
   ```bash
   for ip in $(seq 10 50); do
     curl -X POST http://172.24.1.33:5002/api/switch/map \
       -d "switch_ip=172.24.1.$ip&community=gsmon" > switch_$ip.json
   done
   ```

3. Parsing risultati:
   ```python
   import json

   trunks = []
   for file in glob.glob("switch_*.json"):
       data = json.load(open(file))
       for port in data['ports']:
           if port['is_trunk']:
               trunks.append({
                   'switch': data['switch_name'],
                   'port': port['interface_name'],
                   'vlans': port['tagged_vlans']
               })
   ```

4. Report Excel/CSV

**Risultato**: Lista completa trunk ports con VLAN tagging

---

## 🔐 Security Considerations

### Credenziali

**Problema**: Password salvate in richieste API

**Mitigazioni**:
- Usare HTTPS per tutte le comunicazioni
- Non loggare password in plaintext
- Considerare token-based auth (JWT)
- Vault per gestione credenziali

### Rate Limiting

**Implementato**:
- SSH Terminal: 5 connessioni/min per IP

**Da implementare**:
- ConfigSwitch API: Limitare requests per IP
- Port Mapper: Limitare scansioni simultanee

### Input Validation

**Verificare**:
- IP address format
- SNMP community string sanitization
- SSH command injection prevention

---

## 📈 Future Enhancements

### Priorità Alta

1. **Authentication & Authorization**:
   - User login system
   - Role-based access (admin/operator/viewer)
   - Audit log user actions

2. **Scheduler**:
   - Cron-like scheduler per config automatiche
   - Maintenance windows
   - Rollback automatico

3. **Notification System**:
   - Email alerts per errori
   - Telegram/Slack integration
   - Dashboard allarmi real-time

### Priorità Media

4. **Config Diff & Backup**:
   - Automatic config backup pre-change
   - Git versioning config files
   - Visual diff prima/dopo

5. **Template Library**:
   - Libreria template config riutilizzabili
   - Variabili parametrizzate
   - Versioning templates

6. **Multi-vendor Support**:
   - Estendere a Cisco, Aruba, etc.
   - Universal parser per tutti vendor

### Priorità Bassa

7. **AI/ML Predictions**:
   - Anomaly detection su discovery data
   - Predictive failure analysis
   - Auto-remediation suggestions

8. **Mobile App**:
   - React Native app per monitoring
   - Push notifications
   - Quick config apply

---

## 📚 Riferimenti

### Documentazione Tecnica

- **Huawei CloudEngine Documentation**: https://support.huawei.com
- **SNMP MIBs**: RFC 1213, RFC 2863, Huawei Enterprise MIBs
- **Flask Documentation**: https://flask.palletsprojects.com
- **Paramiko SSH**: https://www.paramiko.org
- **xterm.js**: https://xtermjs.org

### Community

- **Huawei Forum**: https://forum.huawei.com
- **Network Automation Reddit**: r/networking, r/networkautomation

---

**Fine Documentazione**

Versione: 1.0
Ultimo Aggiornamento: 2025-11-15
Autore: Network Management Team
Server: 172.24.1.33
