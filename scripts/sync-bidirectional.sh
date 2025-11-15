#!/bin/bash
# Sync bidirezionale server <-> locale
# Usage: ./sync-bidirectional.sh [pull|push]

set -e

SERVER="mmereu@172.24.1.33"
LOCAL_BASE="$(cd "$(dirname "$0")/.." && pwd)"
DIRECTION="${1:-pull}"

echo "🔄 Network Management - Bidirectional Sync"
echo "=========================================="
echo "Direction: $DIRECTION"
echo "Server: $SERVER"
echo ""

EXCLUDE_OPTS="--exclude=node_modules --exclude=__pycache__ --exclude=*.pyc --exclude=.git --exclude=*.log --exclude=.env"

if [ "$DIRECTION" = "pull" ]; then
    echo "⬇️  Pulling from server..."

    # SSH Terminal
    rsync -avz --progress $EXCLUDE_OPTS \
        "$SERVER:/home/mmereu/ssh-web-terminal/" \
        "$LOCAL_BASE/apps/ssh-terminal/"

    # Backend API
    rsync -avz --progress \
        "$SERVER:/home/mmereu/configswitch/app_huawei_final.py" \
        "$LOCAL_BASE/backend/api/"

    # HTML files
    rsync -avz --progress \
        "$SERVER:/var/www/html/*.html" \
        "$LOCAL_BASE/apps/monitoring/"

    echo "✅ Pull completato"

elif [ "$DIRECTION" = "push" ]; then
    echo "⬆️  Pushing to server..."

    read -p "⚠️  Sei sicuro di voler sovrascrivere i file sul server? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Operazione annullata"
        exit 1
    fi

    # SSH Terminal
    rsync -avz --progress $EXCLUDE_OPTS \
        "$LOCAL_BASE/apps/ssh-terminal/" \
        "$SERVER:/home/mmereu/ssh-web-terminal/"

    # Backend API
    rsync -avz --progress \
        "$LOCAL_BASE/backend/api/app_huawei_final.py" \
        "$SERVER:/home/mmereu/configswitch/"

    # HTML files
    rsync -avz --progress \
        "$LOCAL_BASE/apps/monitoring/*.html" \
        "$SERVER:/var/www/html/"

    echo "✅ Push completato"
    echo "🔄 Ricordati di riavviare i servizi sul server se necessario"

else
    echo "❌ Direction must be 'pull' or 'push'"
    exit 1
fi

echo ""
echo "📊 Sync summary:"
echo "Local:  $LOCAL_BASE"
echo "Server: $SERVER"
