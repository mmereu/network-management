#!/bin/bash
# Backup automatico da server a locale
# Usage: ./backup-from-server.sh [full|incremental]
# Set SERVER_IP environment variable or edit this script

set -e

# Configuration - Set these in your environment or edit here
SERVER_USER="${SERVER_USER:-your_username}"
SERVER_IP="${SERVER_IP:-your_server_ip}"
SERVER="${SERVER_USER}@${SERVER_IP}"
LOCAL_BASE="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$LOCAL_BASE/backups/server-backup-$(date +%Y%m%d-%H%M%S)"
MODE="${1:-incremental}"

echo "Network Management - Server Backup"
echo "======================================"
echo "Mode: $MODE"
echo "Server: $SERVER"
echo "Local: $BACKUP_DIR"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"/{html,backend-api,ssh-terminal,configs}

# Function: download with rsync
download_rsync() {
    local src="$1"
    local dst="$2"
    local exclude="${3:-}"

    echo "Downloading $src..."
    if [ -n "$exclude" ]; then
        rsync -avz --progress --exclude="$exclude" "$SERVER:$src" "$dst"
    else
        rsync -avz --progress "$SERVER:$src" "$dst"
    fi
}

# Download HTML files
download_rsync "/var/www/html/*.html" "$BACKUP_DIR/html/"

# Download Backend APIs
download_rsync "/home/$SERVER_USER/configswitch/app_huawei_final.py" "$BACKUP_DIR/backend-api/"
download_rsync "/home/$SERVER_USER/huawei_vlan/app_switch_mapper.py" "$BACKUP_DIR/backend-api/"

# Download SSH Terminal (if deployed)
if [ "$MODE" = "full" ]; then
    echo "Full backup mode - downloading SSH Terminal..."
    download_rsync "/home/$SERVER_USER/ssh-web-terminal/" "$BACKUP_DIR/ssh-terminal/" "node_modules"
fi

# Download JS/CSS assets
download_rsync "/var/www/html/js/" "$BACKUP_DIR/html/js/"
download_rsync "/var/www/html/css/" "$BACKUP_DIR/html/css/"

# Summary
echo ""
echo "Backup completed!"
echo "Size:"
du -sh "$BACKUP_DIR"/*
echo ""
echo "Path: $BACKUP_DIR"
