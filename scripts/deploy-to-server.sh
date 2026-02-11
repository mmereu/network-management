#!/bin/bash
# Deploy da locale a server
# Usage: ./deploy-to-server.sh [app-name]
# Set SERVER_IP environment variable or edit this script

set -e

# Configuration - Set these in your environment or edit here
SERVER_USER="${SERVER_USER:-your_username}"
SERVER_IP="${SERVER_IP:-your_server_ip}"
SERVER="${SERVER_USER}@${SERVER_IP}"
LOCAL_BASE="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-ssh-terminal}"

echo "Network Management - Deploy to Server"
echo "========================================="
echo "App: $APP"
echo "Server: $SERVER"
echo ""

case "$APP" in
    ssh-terminal)
        echo "Deploying SSH Terminal..."
        rsync -avz --progress \
            --exclude="node_modules" \
            --exclude=".git" \
            --exclude="*.log" \
            "$LOCAL_BASE/apps/ssh-terminal/" \
            "$SERVER:/home/$SERVER_USER/ssh-web-terminal/"

        echo "Restarting SSH Terminal on server..."
        ssh "$SERVER" "cd /home/$SERVER_USER/ssh-web-terminal && pm2 restart ssh-terminal || pm2 start ecosystem.config.js"
        ;;

    backend-api)
        echo "Deploying Backend API..."
        rsync -avz --progress \
            "$LOCAL_BASE/backend/api/app_huawei_final.py" \
            "$SERVER:/home/$SERVER_USER/configswitch/"

        echo "Restarting backend API..."
        ssh "$SERVER" "sudo systemctl restart app-huawei-api"
        ;;

    port-mapper)
        echo "Deploying Port Mapper..."
        rsync -avz --progress \
            "$LOCAL_BASE/apps/port-mapper/app_switch_mapper.py" \
            "$SERVER:/home/$SERVER_USER/huawei_vlan/"

        echo "Restarting port mapper..."
        ssh "$SERVER" "pkill -f app_switch_mapper && cd /home/$SERVER_USER/huawei_vlan && nohup python3 app_switch_mapper.py &"
        ;;

    html)
        echo "Deploying HTML files..."
        rsync -avz --progress \
            "$LOCAL_BASE/apps/monitoring/" \
            "$SERVER:/var/www/html/"
        ;;

    *)
        echo "Unknown app: $APP"
        echo "Available: ssh-terminal, backend-api, port-mapper, html"
        exit 1
        ;;
esac

echo ""
echo "Deploy completed!"
