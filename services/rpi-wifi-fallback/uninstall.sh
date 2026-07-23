#!/bin/bash
set -euo pipefail

echo "[−] Uninstalling Wi-Fi fallback system..."

DEST_DIR="/opt/rpi-wifi-fallback"
SERVICE_PATH="/etc/systemd/system/wifi-fallback.service"
DISPATCHER_PATH="/etc/NetworkManager/dispatcher.d/90-wifi-fallback"
UDEV_RULE="/etc/udev/rules.d/70-wifi-regdom.rules"
POLKIT_RULE_PATH="/etc/polkit-1/rules.d/49-brain-networkmanager.rules"
TMPFILES_PATH="/etc/tmpfiles.d/rpi-wifi-fallback.conf"
RUNTIME_LOCK="/run/rpi-wifi-fallback/operation.lock"
RUNTIME_DIR="/run/rpi-wifi-fallback"
BRAIN_DROPIN_PATH="/etc/systemd/system/brain-monitor.service.d/20-wifi-security.conf"
BRAIN_DROPIN_DIR="/etc/systemd/system/brain-monitor.service.d"

# Stop and disable service
sudo systemctl stop wifi-fallback.service 2>/dev/null || true
sudo systemctl disable wifi-fallback.service 2>/dev/null || true

# Remove the dashboard NetworkManager authorization rule
sudo rm -f "$POLKIT_RULE_PATH"
sudo rm -f "$BRAIN_DROPIN_PATH"
sudo rmdir "$BRAIN_DROPIN_DIR" 2>/dev/null || true

# Remove unit + reload
sudo rm -f "$SERVICE_PATH"
sudo systemctl daemon-reload

# Remove dispatcher + udev rule (if present)
sudo rm -f "$DISPATCHER_PATH" 2>/dev/null || true
sudo rm -f "$UDEV_RULE" 2>/dev/null || true
sudo rm -f "$TMPFILES_PATH" "$RUNTIME_LOCK" 2>/dev/null || true
sudo rmdir "$RUNTIME_DIR" 2>/dev/null || true
sudo udevadm control --reload || true
