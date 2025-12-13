# 🌐 Network Management - Unified Project

**Server**: 172.24.1.33
**Version**: 1.0
**Created**: 2025-11-15

---

## 📋 Overview

Progetto unificato per la gestione completa dell'infrastruttura di rete server 172.24.1.33.

Consolidamento di tutte le applicazioni, backend e frontend in un'unica struttura per facilità di sviluppo, backup e deployment.

---

## 🏗️ Struttura Progetto

```
Network Management/
├── apps/                    # Applicazioni Frontend (~205MB)
│   ├── ssh-terminal/       # SSH Web Terminal (React + xterm.js) - Port 8443 [204MB]
│   │   ├── frontend/       # React app con Vite
│   │   ├── backend/        # Node.js + Express + SSH2
│   │   └── node_modules/   # Dependencies (majority of size)
│   ├── config-switch/      # Config Switch React UI - Port 8443/config-switch [61KB]
│   │   └── app_huawei_final.py  # Flask backend per configurazione switch
│   ├── port-mapper/        # Huawei Port Mapper - Port 5002 [574KB]
│   │   ├── app_switch_mapper.py  # Main Flask app (11KB)
│   │   ├── data_processor.py     # Data processing (18KB)
│   │   ├── requirements.txt      # Python dependencies
│   │   └── frontend/             # Frontend assets
│   ├── migration-tool/     # Migration Tool HP/Huawei → Huawei - Port 9999 [181KB]
│   │   ├── run_PROTECTED.py      # Entry point
│   │   ├── app_PROTECTED/        # Application code
│   │   └── templates_PROTECTED/  # HTML templates
│   ├── monitoring/         # Monitoring Dashboard HTML [48KB]
│   │   ├── monitor_process.html  # Main dashboard (24KB)
│   │   ├── js/monitoring_dashboard.js  # WebSocket client (11KB)
│   │   └── css/style.css         # Styles (11KB)
│   ├── discovery/          # Network Discovery HTML [76KB]
│   │   ├── discovery.html        # SNMP discovery interface (64KB)
│   │   └── css/style.css         # Shared styles
│   └── config-classic/     # Config Switch Classic HTML [64KB]
│       ├── huawei-test.html      # Legacy interface (10KB)
│       ├── configswitch.html     # Alternative interface (10KB)
│       ├── js/configswitch_v6.js # Configuration logic (23KB)
│       └── css/style.css         # Styles
├── backend/                # Backend APIs [96KB]
│   └── api/                # Centralized Flask APIs
│       ├── app_huawei_final.py   # Main API server - Port 5001 (61KB)
│       ├── app_switch_mapper.py  # Port mapper API - Port 5002 (11KB)
│       └── data_processor.py     # Data utilities (18KB)
├── scripts/                # Automation Scripts
│   ├── backup-from-server.sh    # Server → Local backup
│   ├── deploy-to-server.sh      # Local → Server deploy
│   └── sync-bidirectional.sh    # Bidirectional sync
├── docs/                   # Documentazione
├── backups/                # Local backups timestampati
│   └── server-backup-20251115/  # Initial backup [144KB]
│       ├── html/                # All HTML files from /var/www/html/
│       └── backend-api/         # Python backend files
└── README.md               # This file
```

---

## 🎯 Applicazioni (7 totali)

### 1️⃣ SSH Terminal ⭐
- **Path**: `apps/ssh-terminal/`
- **Server**: http://172.24.1.33:8443/
- **Tech**: React + Vite + xterm.js + WebSocket + SSH2
- **Function**: Browser-based SSH client

### 2️⃣ Config Switch (React)
- **Path**: `apps/config-switch/`
- **Server**: http://172.24.1.33:8443/config-switch
- **Tech**: React frontend
- **Function**: Automated switch configuration

### 3️⃣ Port Mapper
- **Path**: `apps/port-mapper/`
- **Server**: http://172.24.1.33:5002
- **Tech**: Flask + SNMP
- **Function**: Port and VLAN mapping

### 4️⃣ Migration Tool
- **Path**: `apps/migration-tool/`
- **Server**: http://172.24.1.33:9999
- **Function**: HP/Huawei → Huawei migration

### 5️⃣ Monitoring Dashboard
- **Path**: `apps/monitoring/`
- **Server**: http://172.24.1.33/monitor_process.html
- **Function**: Real-time process monitoring

### 6️⃣ Network Discovery
- **Path**: `apps/discovery/`
- **Server**: http://172.24.1.33/discovery.html
- **Function**: SNMP device discovery

### 7️⃣ Config Switch Classic
- **Path**: `apps/config-classic/`
- **Server**: http://172.24.1.33/huawei-test.html
- **Function**: Legacy HTML interface

---

## 🔧 Backend API

**Centralized APIs**: `backend/api/`

### Main API (Port 5001)
- **File**: `app_huawei_final.py` (61KB)
- **Function**: Switch configuration via SSH
- **Endpoints**: http://172.24.1.33:5001/api/
- **Used by**: Config Switch React, Config Classic

### Port Mapper API (Port 5002)
- **File**: `app_switch_mapper.py` (11KB)
- **Function**: SNMP port and VLAN mapping
- **Endpoints**: http://172.24.1.33:5002/api/
- **Support**: `data_processor.py` - Data processing utilities

### Migration Tool (Port 9999)
- **File**: `apps/migration-tool/run_PROTECTED.py`
- **Function**: HP/Huawei to Huawei migration
- **URL**: http://172.24.1.33:9999

---

## 🚀 Quick Start

### Development

**React Apps** (SSH Terminal):
```bash
cd apps/ssh-terminal/frontend
npm install
npm run dev  # Frontend on port 5173
```

```bash
cd apps/ssh-terminal/backend
npm install
node server.js  # Backend WebSocket server
```

**Flask Apps** (Config Switch, Port Mapper):
```bash
# Config Switch
cd apps/config-switch
pip install -r requirements.txt  # If requirements exist
python3 app_huawei_final.py --host 0.0.0.0 --port 5001

# Port Mapper
cd apps/port-mapper
pip install -r requirements.txt
python3 app_switch_mapper.py --host 0.0.0.0 --port 5002
```

**Migration Tool**:
```bash
cd apps/migration-tool
pip install -r requirements.txt  # If exists
python3 run_PROTECTED.py
```

**HTML Apps** (Monitoring, Discovery, Config Classic):
- Serve via HTTP server (Apache/Nginx) or Python SimpleHTTPServer
- Already deployed on server at http://172.24.1.33/
- For local testing:
```bash
cd apps/monitoring
python3 -m http.server 8000
# Access at http://localhost:8000/monitor_process.html
```

### Backup from Server

```bash
# Incremental backup (default)
./scripts/backup-from-server.sh

# Full backup (include ssh-terminal)
./scripts/backup-from-server.sh full
```

### Deploy to Server

```bash
# Deploy SSH Terminal
./scripts/deploy-to-server.sh ssh-terminal

# Deploy Backend API
./scripts/deploy-to-server.sh backend-api

# Deploy Port Mapper
./scripts/deploy-to-server.sh port-mapper

# Deploy HTML files
./scripts/deploy-to-server.sh html
```

### Sync Bidirectional

```bash
# Pull from server (safe)
./scripts/sync-bidirectional.sh pull

# Push to server (requires confirmation)
./scripts/sync-bidirectional.sh push
```

---

## 📦 Backup Strategy

### Local Backups

**Path**: `backups/server-backup-YYYYMMDD-HHMMSS/`

**Example**: `backups/server-backup-20251115/` (144KB - initial backup)

**Contents**:
- **html/**: All HTML files from `/var/www/html/`
  - monitor_process.html, discovery.html
  - huawei-test.html, configswitch.html
  - js/ and css/ subdirectories
- **backend-api/**: Python backend files from `/home/mmereu/`
  - app_huawei_final.py (Config Switch API)
  - app_switch_mapper.py (Port Mapper API)
- **ssh-terminal/** (only in full mode): Complete SSH Terminal app
- **configs/**: Configuration files and assets

**Frequency**:
- Manual: before major changes
- Automated: optional daily cron

### Server Backups

Server maintains own backups in `/home/mmereu/backup_*/`

---

## 🔐 Security

**Server Access**:
- SSH: `mmereu@172.24.1.33`
- Key-based authentication recommended
- Scripts use rsync/scp over SSH

**Excluded from Backups**:
- `node_modules/`
- `__pycache__/`
- `*.pyc`
- `.git/` (managed separately)
- `*.log`
- `.env` (sensitive configs)

---

## 📚 Documentation

Full documentation available in `docs/` directory:

- Architecture overview
- API documentation
- Deployment guide
- Development guidelines

---

## 🛠️ Tools Used

- **Bash/Shell**: Automation scripts
- **rsync**: Efficient file synchronization
- **scp**: Secure file copy
- **Git**: Version control (local)
- **SSH**: Server access

---

## 🎨 Homepage Professional

**Main Homepage**: `apps/monitoring/index.html` (26KB) - **Professional Enterprise Dashboard**

### Features
- ✨ **Dark/Light Mode Toggle** - Persistent theme switching
- 🎨 **Modern Glassmorphism Design** - Professional card-based UI
- 📊 **Stats Dashboard** - Real-time metrics overview
- 🚀 **Smooth Animations** - Fade-in effects and hover interactions
- 📱 **Fully Responsive** - Mobile, tablet, desktop optimized
- 💚 **Status Indicators** - Animated pulse indicators
- 🎯 **Interactive Cards** - Hover effects with gradient accents

**Server URL**: http://172.24.1.33/

**Backup Original**: `apps/monitoring/index-original.html` (8.6KB)

---

## 🎯 Next Steps

- [ ] Setup Git repository with `.gitignore`
- [ ] Add CI/CD pipeline
- [ ] Implement automated testing
- [ ] Add monitoring and logging
- [ ] Setup SSL/TLS for production
- [ ] Implement user authentication system

---

## 📞 Support

**Server**: 172.24.1.33
**Admin**: mmereu
**Created**: 2025-11-15

---

**Last Updated**: 2025-11-15
**Version**: 1.0
