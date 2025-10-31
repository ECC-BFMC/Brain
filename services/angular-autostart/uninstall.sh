#!/bin/bash
set -euo pipefail

echo "[−] Uninstalling Angular Dashboard autostart service..."

DEST_DIR="/opt/angular-autostart"
SERVICE_PATH="/etc/systemd/system/angular-dashboard.service"
LOG_FILE="/var/log/angular-dashboard.log"

# Stop and disable service
sudo systemctl stop angular-dashboard.service 2>/dev/null || true
sudo systemctl disable angular-dashboard.service 2>/dev/null || true

# Remove unit + reload
sudo rm -f "$SERVICE_PATH"
sudo systemctl daemon-reload

# Remove application directory and log file
sudo rm -rf "$DEST_DIR"
sudo rm -f "$LOG_FILE"

echo "[−] Angular Dashboard autostart service uninstalled successfully!"