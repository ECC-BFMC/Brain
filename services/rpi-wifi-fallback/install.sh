#!/bin/bash
set -euo pipefail

echo "[+] Installing Wi-Fi fallback project..."

# Paths
DEST_DIR="/opt/rpi-wifi-fallback"
SERVICE_PATH="/etc/systemd/system/wifi-fallback.service"
DISPATCHER_PATH="/etc/NetworkManager/dispatcher.d/90-wifi-fallback"
UDEV_RULE="/etc/udev/rules.d/70-wifi-regdom.rules"
LOG_FILE="/var/log/rpi-wifi-fallback.log"
POLKIT_RULE_PATH="/etc/polkit-1/rules.d/49-brain-networkmanager.rules"

# Create app directory and copy files
sudo mkdir -p "$DEST_DIR"
sudo cp fallback.sh config.env "$DEST_DIR/"

# Allow the non-interactive dashboard service user to manage NetworkManager.
sudo install -D -o root -g root -m 0644 49-brain-networkmanager.rules "$POLKIT_RULE_PATH"

# Normalize line endings (avoid hidden \r from Windows editors)
sudo sed -i 's/\r$//' "$DEST_DIR/fallback.sh" "$DEST_DIR/config.env"

# Make script executable
sudo chmod +x "$DEST_DIR/fallback.sh"

# Log file (service runs as root, so 0644 is fine)
sudo touch "$LOG_FILE"
sudo chmod 0644 "$LOG_FILE"

# Install (or update) systemd unit
sudo cp wifi-fallback.service "$SERVICE_PATH"
sudo systemctl daemon-reload

sudo systemctl enable --now wifi-fallback.service

echo "[+] RPi Wifi Fallback service installed successfully!"