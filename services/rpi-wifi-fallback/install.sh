#!/bin/bash
set -euo pipefail

echo "[+] Installing Wi-Fi fallback project..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Paths
DEST_DIR="/opt/rpi-wifi-fallback"
SERVICE_PATH="/etc/systemd/system/wifi-fallback.service"
DISPATCHER_PATH="/etc/NetworkManager/dispatcher.d/90-wifi-fallback"
UDEV_RULE="/etc/udev/rules.d/70-wifi-regdom.rules"
LOG_FILE="/var/log/rpi-wifi-fallback.log"
POLKIT_RULE_PATH="/etc/polkit-1/rules.d/49-brain-networkmanager.rules"
TMPFILES_PATH="/etc/tmpfiles.d/rpi-wifi-fallback.conf"
BRAIN_DROPIN_PATH="/etc/systemd/system/brain-monitor.service.d/20-wifi-security.conf"

# Give only the dashboard service a stable identity that Polkit can match.
if ! getent group brain-network >/dev/null; then
  sudo groupadd --system brain-network
fi
sudo usermod --append --groups brain-network pi

# Create app directory and copy files
sudo mkdir -p "$DEST_DIR"
sudo cp fallback.sh add-wifi.sh config.env "$DEST_DIR/"

# Allow the non-interactive dashboard service user to manage NetworkManager.
sudo install -D -o root -g root -m 0644 49-brain-networkmanager.rules "$POLKIT_RULE_PATH"
sudo install -D -o root -g root -m 0644 brain-monitor-wifi.conf "$BRAIN_DROPIN_PATH"

# Re-run fallback reconciliation whenever a client Wi-Fi connection goes down.
sudo install -D -o root -g root -m 0755 90-wifi-fallback "$DISPATCHER_PATH"

# The root fallback service and the pi dashboard use this lock to serialize radio changes.
sudo install -D -o root -g root -m 0644 rpi-wifi-fallback.conf "$TMPFILES_PATH"

# Normalize line endings (avoid hidden \r from Windows editors)
sudo sed -i 's/\r$//' \
  "$DEST_DIR/fallback.sh" \
  "$DEST_DIR/add-wifi.sh" \
  "$DEST_DIR/config.env" \
  "$DISPATCHER_PATH" \
  "$TMPFILES_PATH" \
  "$BRAIN_DROPIN_PATH"

sudo systemd-tmpfiles --create "$TMPFILES_PATH"

# Make script executable
sudo chmod +x "$DEST_DIR/fallback.sh" "$DEST_DIR/add-wifi.sh"

# Log file (service runs as root, so 0644 is fine)
sudo touch "$LOG_FILE"
sudo chmod 0644 "$LOG_FILE"

# Install (or update) systemd unit
sudo cp wifi-fallback.service "$SERVICE_PATH"
sudo systemctl daemon-reload
sudo systemctl try-restart brain-monitor.service || true

sudo systemctl enable wifi-fallback.service
sudo systemctl restart wifi-fallback.service

echo "[+] RPi Wifi Fallback service installed successfully!"
