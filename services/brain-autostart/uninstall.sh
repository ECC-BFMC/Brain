#!/bin/bash
set -euo pipefail

echo "[−] Uninstalling Brain monitor service..."

DEST_DIR="/opt/brain-autostart"
SERVICE_PATH="/etc/systemd/system/brain-monitor.service"
LOG_FILE="/var/log/brain-monitor.log"

# Stop and disable service
sudo systemctl stop brain-monitor.service 2>/dev/null || true
sudo systemctl disable brain-monitor.service 2>/dev/null || true

# Remove unit + reload
sudo rm -f "$SERVICE_PATH"
sudo systemctl daemon-reload

# Remove application directory and log file
sudo rm -rf "$DEST_DIR"
sudo rm -f "$LOG_FILE"

echo "[−] Brain monitor service uninstalled successfully!"