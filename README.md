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
├── apps/                    # Applicazioni Frontend
│   ├── ssh-terminal/       # SSH Web Terminal (React + xterm.js) - Port 8443
│   ├── config-switch/      # Config Switch React UI - Port 8443/config-switch
│   ├── port-mapper/        # Huawei Port Mapper - Port 5002
│   ├── migration-tool/     # Migration Tool - Port 9999
│   ├── monitoring/         # Monitoring Dashboard HTML
│   ├── discovery/          # Network Discovery HTML
│   └── config-classic/     # Config Switch Classic HTML
├── backend/                # Backend APIs
│   ├── api/                # Flask APIs (app_huawei_final.py - Port 5001)
│   └── shared/             # Shared utilities
├── scripts/                # Automation Scripts
│   ├── backup-from-server.sh    # Server → Local backup
│   ├── deploy-to-server.sh      # Local → Server deploy
│   └── sync-bidirectional.sh    # Bidirectional sync
├── docs/                   # Documentazione
├── backups/                # Local backups timestampati
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

**Main API**: `backend/api/app_huawei_final.py`
**Port**: 5001
**Endpoints**: http://172.24.1.33:5001/api/

---

## 🚀 Quick Start

### Development

```bash
# SSH Terminal (esempio)
cd apps/ssh-terminal
npm run dev
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

**Contents**:
- HTML files from `/var/www/html/`
- Backend APIs from `/home/mmereu/`
- Configs and assets

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
