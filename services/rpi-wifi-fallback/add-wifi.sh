#!/bin/bash
set -euo pipefail

# Usage: sudo ./add-wifi.sh "SSID" "PASSWORD" yes
# Logs are appended to the same file used by fallback.sh

TARGET_SSID="${1:-}"
TARGET_PSK="${2:-}"
AUTOCONNECT="${3:-}"

if [[ -z "$TARGET_SSID" || -z "$TARGET_PSK" || -z "$AUTOCONNECT" ]]; then
  echo "Usage: $0 <SSID> <PASSWORD> <autoconnect: yes|no>"
  exit 1
fi

# ---------- detach so SSH drop won't kill the run ----------
if [[ "${ADDWIFI_DETACHED:-0}" != "1" ]]; then
  SCRIPT="$(realpath "$0")"
  UNIT="rpi-add-wifi-$(date +%s)"
  LOG="/var/log/rpi-wifi-fallback.log"
  if ! sudo sh -c "mkdir -p /var/log && touch '$LOG' && chmod 0644 '$LOG'"; then
    # last resort; still detach, but fallback.sh also logs here
    LOG="/tmp/rpi-wifi-fallback.log"
    touch "$LOG"
  fi
  if command -v systemd-run >/dev/null 2>&1; then
    sudo systemd-run --unit "$UNIT" --collect \
      -p StandardOutput=append:"$LOG" \
      -p StandardError=append:"$LOG" \
      -p WorkingDirectory="$(pwd)" \
      /bin/bash -c "ADDWIFI_DETACHED=1 '$SCRIPT' \"$TARGET_SSID\" \"$TARGET_PSK\" \"$AUTOCONNECT\""
    echo "[info] Launched: $UNIT"; echo "[info] Follow: sudo tail -f '$LOG'"
    exit 0
  else
    ( ADDWIFI_DETACHED=1 "$SCRIPT" "$TARGET_SSID" "$TARGET_PSK" "$AUTOCONNECT" ) \
      >>"$LOG" 2>&1 < /dev/null &
    disown || true
    echo "[info] Running in background. Log: $LOG"
    exit 0
  fi
fi

# ---------- worker (same style as fallback.sh) ----------
LOG="/var/log/rpi-wifi-fallback.log"
mkdir -p /var/log
touch "$LOG" 2>/dev/null || true
exec &> >(tee -a "$LOG")

CONFIG_FILE="/opt/rpi-wifi-fallback/config.env"
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

# --- helpers copied from fallback.sh style ---
strip_crnl() { printf '%s' "$1" | tr -d '\r\n'; }
say() { echo "[$(date +'%F %T')] $*"; }
run_nmcli() { command -v sudo &>/dev/null && sudo nmcli "$@" || nmcli "$@"; }

# --- config (with CR/LF sanitizing) ---
IFACE=$(strip_crnl "${IFACE:-wlan0}")
AP_CON_NAME=$(strip_crnl "${CON_NAME:-rpi-hotspot}")
HOTSPOT_SSID=$(strip_crnl "${SSID:-BFMCDemoCar}")
DELETE_AP_ON_CLIENT=$(strip_crnl "${DELETE_AP_ON_CLIENT:-true}")

TARGET_SSID="$(strip_crnl "$TARGET_SSID")"
TARGET_PSK="$(strip_crnl "$TARGET_PSK")"
AUTOCONNECT="$(strip_crnl "$AUTOCONNECT")"

# Safety: don't try to join our own hotspot
if [[ "$TARGET_SSID" == "$AP_CON_NAME" || "$TARGET_SSID" == "$HOTSPOT_SSID" ]]; then
  say "[!] '$TARGET_SSID' matches hotspot ('$AP_CON_NAME' / '$HOTSPOT_SSID'); aborting."
  exit 1
fi

ensure_iface_idle() {
  say "Ensuring $IFACE is managed & idle"
  run_nmcli device set "$IFACE" managed yes || true
  # Stop any active Wi-Fi (AP or client) on this iface
  mapfile -t active_uuids < <( nmcli -t -f NAME,UUID,TYPE,DEVICE,ACTIVE con show --active \
      | awk -F: -v ifc="$IFACE" '$3=="wifi" && $4==ifc && $5=="yes"{print $2}' || true )
  for uuid in "${active_uuids[@]}"; do
    [[ -z "$uuid" ]] && continue
    # prevent AP autospawn while we switch to client
    run_nmcli con modify "$AP_CON_NAME" connection.autoconnect no 2>/dev/null || true
    run_nmcli con modify "$AP_CON_NAME" connection.autoconnect-priority 0 2>/dev/null || true
    say "Deactivating Wi-Fi on $IFACE (uuid: $uuid)"
    run_nmcli -w 10 con down uuid "$uuid" || true
  done
  run_nmcli device disconnect "$IFACE" || true
  sleep 1
}

restore_hotspot_on_failure() {
  say "Restoring hotspot '$AP_CON_NAME' for access..."
  if ! nmcli -t -f NAME con show | grep -Fxq "$AP_CON_NAME"; then
    run_nmcli con add type wifi ifname "$IFACE" con-name "$AP_CON_NAME" ssid "$HOTSPOT_SSID"
    run_nmcli con modify "$AP_CON_NAME" \
      connection.autoconnect no \
      802-11-wireless.mode ap \
      802-11-wireless.band bg \
      ipv4.method shared \
      ipv6.method ignore
  fi
  run_nmcli con modify "$AP_CON_NAME" connection.autoconnect no || true
  if ! run_nmcli -w 20 -o con up "$AP_CON_NAME"; then
    say "⚠ Failed to bring hotspot up automatically."
  fi
}

say "===== add-wifi start (iface:$IFACE target:'$TARGET_SSID' autoconnect:$AUTOCONNECT) ====="

# 1) Idle interface & stop hotspot
ensure_iface_idle

# 2) Create/replace client profile (prefer 5 GHz)
say "Creating Wi-Fi profile '$TARGET_SSID' (preferring 5 GHz)"
run_nmcli connection delete "$TARGET_SSID" 2>/dev/null || true
run_nmcli connection add type wifi ifname "$IFACE" con-name "$TARGET_SSID" ssid "$TARGET_SSID"
run_nmcli connection modify "$TARGET_SSID" \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$TARGET_PSK" \
  802-11-wireless.mode infrastructure \
  802-11-wireless.band a \
  802-11-wireless.cloned-mac-address permanent \
  connection.autoconnect "$AUTOCONNECT" \
  connection.autoconnect-priority 20

# 3) Try to connect (3 short attempts)
RETRIES=3; WAIT=25; ok=0
for ((i=1;i<=RETRIES;i++)); do
  say "Attempt $i/$RETRIES: scan + connect..."
  run_nmcli dev wifi rescan ifname "$IFACE" || true
  sleep 2
  if run_nmcli -w "$WAIT" -o connection up "$TARGET_SSID"; then
    ok=1; break
  fi
  say "Attempt $i failed. Device snapshot:"
  nmcli -f GENERAL,IP4,IP6 device show "$IFACE" || true
  nmcli -t -f STATE g || true
done

if (( ok )); then
  say "✓ Connected to '$TARGET_SSID'."
  if [[ "${DELETE_AP_ON_CLIENT,,}" == "true" ]]; then
    if nmcli -t -f NAME con show | grep -Fxq "$AP_CON_NAME"; then
      say "Deleting AP profile '$AP_CON_NAME' (DELETE_AP_ON_CLIENT=true)."
      run_nmcli con delete "$AP_CON_NAME" || true
    fi
  fi
  ip -4 addr show "$IFACE" | awk '/inet /{print "✓ IP:", $2}'
  ip route | awk '/default/{print "Default route:", $0}'
  say "Done."
  exit 0
fi

say "Could not connect to '$TARGET_SSID'."
# Optional: capture a tiny recent NM excerpt into the same log (kept short)
if command -v journalctl >/dev/null 2>&1; then
  say "Recent NetworkManager logs (last 3 min):"
  journalctl -u NetworkManager --since "3 min ago" -n 200 --no-pager || true
  journalctl -u wpa_supplicant --since "3 min ago" -n 120 --no-pager || true
fi

# 4) Restore hotspot so you can reconnect
restore_hotspot_on_failure
say "Saved profile. You can retry manually with: nmcli -w $WAIT -o connection up \"$TARGET_SSID\""
exit 1
