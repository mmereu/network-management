# Network Management - Unified Project

**Version**: 1.0
**Created**: 2025-11-15

---

## Overview

Progetto unificato per la gestione completa dell'infrastruttura di rete.

Consolidamento di tutte le applicazioni, backend e frontend in un'unica struttura per facilità di sviluppo, backup e deployment.

**Requisiti**: Installare su un server Linux con Python 3.10+ e Node.js 18+.

---

## Struttura Progetto

```
Network Management/
├── apps/                    # Applicazioni Frontend
│   ├── ssh-terminal/       # SSH Web Terminal (React + xterm.js) - Port 8443
│   │   ├── frontend/       # React app con Vite
│   │   ├── backend/        # Node.js + Express + SSH2
│   │   └── node_modules/   # Dependencies
│   ├── config-switch/      # Config Switch React UI - Port 8443/config-switch
│   │   └── app_huawei_final.py  # Flask backend per configurazione switch
│   ├── port-mapper/        # Huawei Port Mapper - Port 5002
│   │   ├── app_switch_mapper.py  # Main Flask app
│   │   ├── data_processor.py     # Data processing
│   │   ├── requirements.txt      # Python dependencies
│   │   └── frontend/             # Frontend assets
│   ├── migration-tool/     # Migration Tool HP/Huawei → Huawei - Port 9999
│   │   ├── run_PROTECTED.py      # Entry point
│   │   ├── app_PROTECTED/        # Application code
│   │   └── templates_PROTECTED/  # HTML templates
│   ├── monitoring/         # Monitoring Dashboard HTML
│   │   ├── monitor_process.html  # Main dashboard
│   │   ├── js/monitoring_dashboard.js  # WebSocket client
│   │   └── css/style.css         # Styles
│   ├── discovery/          # Network Discovery HTML
│   │   ├── discovery.html        # SNMP discovery interface
│   │   └── css/style.css         # Shared styles
│   └── config-classic/     # Config Switch Classic HTML
│       ├── huawei-test.html      # Legacy interface
│       ├── configswitch.html     # Alternative interface
│       ├── js/configswitch_v6.js # Configuration logic
│       └── css/style.css         # Styles
├── backend/                # Backend APIs
│   └── api/                # Centralized Flask APIs
│       ├── app_huawei_final.py   # Main API server - Port 5001
│       ├── app_switch_mapper.py  # Port mapper API - Port 5002
│       └── data_processor.py     # Data utilities
├── scripts/                # Automation Scripts
│   ├── backup-from-server.sh    # Server → Local backup
│   ├── deploy-to-server.sh      # Local → Server deploy
│   └── sync-bidirectional.sh    # Bidirectional sync
├── docs/                   # Documentazione
└── README.md               # This file
```

---

## Applicazioni (7 totali)

### 1. SSH Terminal
- **Path**: `apps/ssh-terminal/`
- **Port**: 8443
- **Tech**: React + Vite + xterm.js + WebSocket + SSH2
- **Function**: Browser-based SSH client

### 2. Config Switch (React)
- **Path**: `apps/config-switch/`
- **Port**: 8443/config-switch
- **Tech**: React frontend
- **Function**: Automated switch configuration

### 3. Port Mapper
- **Path**: `apps/port-mapper/`
- **Port**: 5002
- **Tech**: Flask + SNMP
- **Function**: Port and VLAN mapping

### 4. Migration Tool
- **Path**: `apps/migration-tool/`
- **Port**: 9999
- **Function**: HP/Huawei → Huawei migration
- **Features**: SSH/Telnet fallback, modern dark UI

### 5. Monitoring Dashboard
- **Path**: `apps/monitoring/`
- **Port**: 80 (HTTP)
- **Function**: Real-time process monitoring

### 6. Network Discovery
- **Path**: `apps/discovery/`
- **Port**: 80 (HTTP)
- **Function**: SNMP device discovery

### 7. Config Switch Classic
- **Path**: `apps/config-classic/`
- **Port**: 80 (HTTP)
- **Function**: Legacy HTML interface

---

## Backend API

**Centralized APIs**: `backend/api/`

### Main API (Port 5001)
- **File**: `app_huawei_final.py`
- **Function**: Switch configuration via SSH
- **Used by**: Config Switch React, Config Classic

### Port Mapper API (Port 5002)
- **File**: `app_switch_mapper.py`
- **Function**: SNMP port and VLAN mapping
- **Support**: `data_processor.py` - Data processing utilities

### Migration Tool (Port 9999)
- **File**: `apps/migration-tool/run_PROTECTED.py`
- **Function**: HP/Huawei to Huawei migration

---

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mmereu/network-management.git
cd network-management
```

2. Install Python dependencies:
```bash
pip install flask netmiko jinja2
```

3. Install Node.js dependencies (for SSH Terminal):
```bash
cd apps/ssh-terminal/frontend && npm install
cd ../backend && npm install
```

### Running Applications

**React Apps** (SSH Terminal):
```bash
cd apps/ssh-terminal/frontend
npm run dev  # Frontend on port 5173

cd apps/ssh-terminal/backend
node server.js  # Backend WebSocket server
```

**Flask Apps** (Config Switch, Port Mapper):
```bash
# Config Switch
cd apps/config-switch
python3 app_huawei_final.py --host 0.0.0.0 --port 5001

# Port Mapper
cd apps/port-mapper
python3 app_switch_mapper.py --host 0.0.0.0 --port 5002
```

**Migration Tool**:
```bash
cd apps/migration-tool
python3 run_PROTECTED.py  # Runs on port 9999
```

**HTML Apps** (Monitoring, Discovery, Config Classic):
```bash
# Serve via HTTP server (Apache/Nginx) or Python
cd apps/monitoring
python3 -m http.server 8000
# Access at http://localhost:8000/monitor_process.html
```

---

## Security

**Excluded from Repository**:
- `node_modules/`
- `__pycache__/`
- `*.pyc`
- `*.log`
- `.env` (sensitive configs)

**Recommendations**:
- Use key-based SSH authentication
- Setup SSL/TLS for production
- Implement user authentication system

---

## Documentation

Full documentation available in `docs/` directory:

- Architecture overview
- API documentation
- Deployment guide
- Development guidelines

---

## Tools Used

- **Python 3.10+**: Flask, Netmiko, Jinja2
- **Node.js 18+**: React, Express, SSH2
- **Bash/Shell**: Automation scripts
- **Git**: Version control

---

## Next Steps

- [ ] Add CI/CD pipeline
- [ ] Implement automated testing
- [ ] Add monitoring and logging
- [ ] Setup SSL/TLS for production
- [ ] Implement user authentication system

---

**Last Updated**: 2025-12-13
**Version**: 1.0
