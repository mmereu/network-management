#!/bin/bash
# Sync bidirezionale server <-> locale
# Usage: ./sync-bidirectional.sh [pull|push]
# Set SERVER_IP environment variable or edit this script

set -e

# Configuration - Set these in your environment or edit here
SERVER_USER="${SERVER_USER:-your_username}"
SERVER_IP="${SERVER_IP:-your_server_ip}"
SERVER="${SERVER_USER}@${SERVER_IP}"
LOCAL_BASE="$(cd "$(dirname "$0")/.." && pwd)"
DIRECTION="${1:-pull}"

echo "Network Management - Bidirectional Sync"
echo "=========================================="
echo "Direction: $DIRECTION"
echo "Server: $SERVER"
echo ""

EXCLUDE_OPTS="--exclude=node_modules --exclude=__pycache__ --exclude=*.pyc --exclude=.git --exclude=*.log --exclude=.env"

if [ "$DIRECTION" = "pull" ]; then
    echo "Pulling from server..."

    # SSH Terminal
    rsync -avz --progress $EXCLUDE_OPTS \
        "$SERVER:/home/$SERVER_USER/ssh-web-terminal/" \
        "$LOCAL_BASE/apps/ssh-terminal/"

    # Backend API
    rsync -avz --progress \
        "$SERVER:/home/$SERVER_USER/configswitch/app_huawei_final.py" \
        "$LOCAL_BASE/backend/api/"

    # HTML files
    rsync -avz --progress \
        "$SERVER:/var/www/html/*.html" \
        "$LOCAL_BASE/apps/monitoring/"

    echo "Pull completed"

elif [ "$DIRECTION" = "push" ]; then
    echo "Pushing to server..."

    read -p "WARNING: Are you sure you want to overwrite files on the server? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled"
        exit 1
    fi

    # SSH Terminal
    rsync -avz --progress $EXCLUDE_OPTS \
        "$LOCAL_BASE/apps/ssh-terminal/" \
        "$SERVER:/home/$SERVER_USER/ssh-web-terminal/"

    # Backend API
    rsync -avz --progress \
        "$LOCAL_BASE/backend/api/app_huawei_final.py" \
        "$SERVER:/home/$SERVER_USER/configswitch/"

    # HTML files
    rsync -avz --progress \
        "$LOCAL_BASE/apps/monitoring/*.html" \
        "$SERVER:/var/www/html/"

    echo "Push completed"
    echo "Remember to restart services on the server if needed"

else
    echo "Direction must be 'pull' or 'push'"
    exit 1
fi

echo ""
echo "Sync summary:"
echo "Local:  $LOCAL_BASE"
echo "Server: $SERVER"
