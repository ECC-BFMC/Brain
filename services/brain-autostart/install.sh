#!/bin/bash
set -euo pipefail

echo "[+] Installing Brain monitor service..."

# Change to the script's directory
cd "$(dirname "$0")"

# Paths
DEST_DIR="/opt/brain-autostart"
SERVICE_PATH="/etc/systemd/system/brain-monitor.service"
LOG_FILE="/var/log/brain-monitor.log"

# Create app directory and copy files
sudo mkdir -p "$DEST_DIR"
sudo cp monitor-dashboard.sh start-brain.sh config.env "$DEST_DIR/"

# Normalize line endings
sudo sed -i 's/\r$//' "$DEST_DIR/monitor-dashboard.sh" "$DEST_DIR/start-brain.sh" "$DEST_DIR/config.env"

# Make scripts executable
sudo chmod +x "$DEST_DIR/monitor-dashboard.sh" "$DEST_DIR/start-brain.sh"

# Log file
sudo touch "$LOG_FILE"
sudo chown pi:pi "$LOG_FILE"
sudo chmod 0644 "$LOG_FILE"

# Install systemd unit
sudo cp brain-monitor.service "$SERVICE_PATH"
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable brain-monitor.service
sudo systemctl start brain-monitor.service

echo "[+] Brain monitor service installed successfully!"