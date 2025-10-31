#!/bin/bash
set -euo pipefail

echo "[−] Uninstalling Wi-Fi fallback system..."

DEST_DIR="/opt/rpi-wifi-fallback"
SERVICE_PATH="/etc/systemd/system/wifi-fallback.service"
DISPATCHER_PATH="/etc/NetworkManager/dispatcher.d/90-wifi-fallback"
UDEV_RULE="/etc/udev/rules.d/70-wifi-regdom.rules"

# Stop and disable service
sudo systemctl stop wifi-fallback.service 2>/dev/null || true
sudo systemctl disable wifi-fallback.service 2>/dev/null || true

# Remove unit + reload
sudo rm -f "$SERVICE_PATH"
sudo systemctl daemon-reload

# Remove dispatcher + udev rule (if present)
sudo rm -f "$DISPATCHER_PATH" 2>/dev/null || true
sudo rm -f "$UDEV_RULE" 2>/dev/null || true
sudo udevadm control --reload || true