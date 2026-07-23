#!/bin/bash
set -euo pipefail

echo "[+] Installing Wi-Fi fallback project..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Authenticate once, before making any changes. Running this script as the
# regular `pi` user from an interactive terminal will prompt for its sudo
# password. Running it through `sudo` remains supported.
declare -a ROOT_COMMAND=()
if (( EUID != 0 )); then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[!] This installer needs administrator privileges, but sudo was not found." >&2
    exit 1
  fi
  echo "[i] Administrator privileges are required to install the Wi-Fi service."
  if ! sudo -v; then
    echo "[!] Sudo authentication failed. Run this installer from an interactive SSH or local terminal." >&2
    exit 1
  fi
  ROOT_COMMAND=(sudo)
fi

as_root() {
  "${ROOT_COMMAND[@]}" "$@"
}

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
  as_root groupadd --system brain-network
fi
as_root usermod --append --groups brain-network pi

# Create app directory and copy files
as_root mkdir -p "$DEST_DIR"
as_root cp fallback.sh add-wifi.sh config.env "$DEST_DIR/"

# Allow the non-interactive dashboard service user to manage NetworkManager.
as_root install -D -o root -g root -m 0644 49-brain-networkmanager.rules "$POLKIT_RULE_PATH"
as_root install -D -o root -g root -m 0644 brain-monitor-wifi.conf "$BRAIN_DROPIN_PATH"

# Re-run fallback reconciliation whenever a client Wi-Fi connection goes down.
as_root install -D -o root -g root -m 0755 90-wifi-fallback "$DISPATCHER_PATH"

# The root fallback service and the pi dashboard use this lock to serialize radio changes.
as_root install -D -o root -g root -m 0644 rpi-wifi-fallback.conf "$TMPFILES_PATH"

# Normalize line endings (avoid hidden \r from Windows editors)
as_root sed -i 's/\r$//' \
  "$DEST_DIR/fallback.sh" \
  "$DEST_DIR/add-wifi.sh" \
  "$DEST_DIR/config.env" \
  "$DISPATCHER_PATH" \
  "$TMPFILES_PATH" \
  "$BRAIN_DROPIN_PATH"

as_root systemd-tmpfiles --create "$TMPFILES_PATH"

# Make script executable
as_root chmod +x "$DEST_DIR/fallback.sh" "$DEST_DIR/add-wifi.sh"

# Log file (service runs as root, so 0644 is fine)
as_root touch "$LOG_FILE"
as_root chmod 0644 "$LOG_FILE"

# Install (or update) systemd unit
as_root cp wifi-fallback.service "$SERVICE_PATH"
as_root systemctl daemon-reload
as_root systemctl try-restart brain-monitor.service || true

as_root systemctl enable wifi-fallback.service
as_root systemctl restart wifi-fallback.service

echo "[+] RPi Wifi Fallback service installed successfully!"
