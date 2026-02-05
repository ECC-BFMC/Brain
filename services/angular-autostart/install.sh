#!/bin/bash
set -euo pipefail

echo "[+] Installing Angular Dashboard autostart service..."

# Paths
DEST_DIR="/opt/angular-autostart"
SERVICE_PATH="/etc/systemd/system/angular-dashboard.service"
LOG_FILE="/var/log/angular-dashboard.log"

# Create app directory and copy files
sudo mkdir -p "$DEST_DIR"
sudo cp start-dashboard.sh config.env "$DEST_DIR/"

# Normalize line endings (avoid hidden \r from Windows editors)
sudo sed -i 's/\r$//' "$DEST_DIR/start-dashboard.sh" "$DEST_DIR/config.env"

# Make script executable
sudo chmod +x "$DEST_DIR/start-dashboard.sh"

# Log file
sudo touch "$LOG_FILE"
sudo chown pi:pi "$LOG_FILE"
sudo chmod 0644 "$LOG_FILE"

# Install (or update) systemd unit
sudo cp angular-dashboard.service "$SERVICE_PATH"
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable angular-dashboard.service
sudo systemctl start angular-dashboard.service

echo "[+] Angular Dashboard autostart service installed successfully!"