#!/bin/bash
set -euo pipefail

LOG="/var/log/rpi-wifi-fallback.log"
exec &> >(tee -a "$LOG")

CONFIG_FILE="/opt/rpi-wifi-fallback/config.env"
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

# --- config (with CR/LF sanitizing) ---
strip_crnl() { printf '%s' "$1" | tr -d '\r\n'; }
SSID=$(strip_crnl "${SSID:-Test}")
PASSWORD=$(strip_crnl "${PASSWORD:-supersecurepassword}")
IFACE=$(strip_crnl "${IFACE:-wlan0}")
CON_NAME=$(strip_crnl "${CON_NAME:-rpi-hotspot}")
BAND=$(strip_crnl "${BAND:-bg}")
CHANNEL=$(strip_crnl "${CHANNEL:-6}")

# How long to wait at boot / when disconnected for client Wi-Fi to come up
GRACE_CONNECT_SECONDS=${GRACE_CONNECT_SECONDS:-25}

# Delete the AP profile on client connect? (true/false)
DELETE_AP_ON_CLIENT=${DELETE_AP_ON_CLIENT:-true}

run_nmcli() { command -v sudo &>/dev/null && sudo nmcli "$@" || nmcli "$@"; }
say() { echo "[$(date +'%F %T')] $*"; }

# single-instance lock
mkdir -p /run
exec 9>"/run/rpi-wifi-fallback.lock"
if ! flock -n 9; then
  say "Another instance is running; exiting."
  exit 0
fi

nm_state() { nmcli -t -f STATE g 2>/dev/null || echo unknown; }
dev_state() { nmcli -t -f GENERAL.STATE device show "$IFACE" 2>/dev/null | cut -d: -f2 || true; }

check_wifi_state() {
  local s1 s2
  s1=$(nm_state); sleep 1; s2=$(nm_state)
  [[ "$s1" == "connected" && "$s2" == "connected" ]] && echo connected || echo disconnected
}

wait_for_client() {
  say "Waiting up to ${GRACE_CONNECT_SECONDS}s for client Wi-Fi..."
  # Prefer nm-online if available (quiet, succeed only if 'online')
  if command -v nm-online >/dev/null 2>&1; then
    if nm-online -q -t "$GRACE_CONNECT_SECONDS"; then
      say "nm-online: system is online."
      return 0
    fi
  else
    # Poll NM state
    local t=$GRACE_CONNECT_SECONDS
    while (( t-- > 0 )); do
      [[ "$(check_wifi_state)" == "connected" ]] && return 0
      sleep 1
    done
  fi
  say "Client Wi-Fi did not come up within grace period."
  return 1
}

ensure_iface_idle() {
  say "Ensuring $IFACE is managed and idle (dev-state: $(dev_state || echo '?'))"
  run_nmcli device set "$IFACE" managed yes || true
  run_nmcli device disconnect "$IFACE" || true
  sleep 1
}

delete_transient_hotspots() {
  mapfile -t leftovers < <( run_nmcli -t -f NAME,TYPE con show \
      | awk -F: '$2=="wifi"{print $1}' \
      | grep -Ei '^(Hotspot(-[0-9]+)?)$' || true )
  for n in "${leftovers[@]}"; do
    [[ -z "$n" ]] && continue
    say "Deleting transient hotspot connection: $n"
    run_nmcli con delete "$n" || true
  done
}

bring_up_ap() {
  say "Preparing hotspot profile '$CON_NAME' on $IFACE (SSID:'$SSID' band:$BAND ch:$CHANNEL)"
  ensure_iface_idle
  delete_transient_hotspots

  # Create or update AP profile; IMPORTANT: autoconnect is OFF
  if ! run_nmcli -t -f NAME con show | grep -Fxq "$CON_NAME"; then
    run_nmcli con add type wifi ifname "$IFACE" con-name "$CON_NAME" ssid "$SSID"
  fi

  run_nmcli con modify "$CON_NAME" \
    connection.autoconnect no \
    connection.autoconnect-priority 0 \
    802-11-wireless.mode ap \
    802-11-wireless.band "$BAND" \
    802-11-wireless.channel "$CHANNEL" \
    802-11-wireless.hidden no \
    802-11-wireless-security.key-mgmt wpa-psk \
    802-11-wireless-security.proto rsn \
    802-11-wireless-security.group ccmp \
    802-11-wireless-security.pairwise ccmp \
    802-11-wireless-security.psk "$PASSWORD" \
    ipv4.method shared \
    ipv4.addresses 192.168.50.1/24 \
    ipv6.method ignore

  say "Bringing up hotspot '$CON_NAME' (manual start)..."
  if ! run_nmcli -w 20 -o con up "$CON_NAME"; then
    say "Hotspot activation failed. Device status:"
    run_nmcli -f GENERAL,IP4 device show "$IFACE" || true
    say "Recent NetworkManager / wpa_supplicant logs:"
    journalctl -u NetworkManager --since "3 min ago" -n 400 --no-pager || true
    journalctl -b -u wpa_supplicant -n 200 --no-pager || true
    exit 1
  fi

  sleep 2
  ip -4 addr show "$IFACE" | awk '/inet /{print "✓ Hotspot IP:", $2; found=1} END{if(!found) print "IP pending..."}'
}

bring_down_ap() {
  say "Bringing hotspot '$CON_NAME' down (if active)..."

  # ensure AP won't autostart again
  if run_nmcli -t -f NAME con show | grep -Fxq "$CON_NAME"; then
    run_nmcli con modify "$CON_NAME" connection.autoconnect no || true
    run_nmcli con modify "$CON_NAME" connection.autoconnect-priority 0 || true
  fi

  # Deactivate any active AP on this iface by UUID
  mapfile -t active_uuids < <( nmcli -t -f NAME,UUID,TYPE,DEVICE,ACTIVE con show --active \
      | awk -F: -v ifc="$IFACE" '$3=="wifi" && $4==ifc && $5=="yes"{print $2}' || true )
  for uuid in "${active_uuids[@]}"; do
    [[ -z "$uuid" ]] && continue
    say "Deactivating active AP UUID: $uuid"
    run_nmcli -w 10 con down uuid "$uuid" || true
  done

  delete_transient_hotspots

  if [[ "${DELETE_AP_ON_CLIENT,,}" == "true" ]]; then
    if run_nmcli -t -f NAME con show | grep -Fxq "$CON_NAME"; then
      say "Deleting AP profile '$CON_NAME' on client connect."
      run_nmcli con delete "$CON_NAME" || true
    fi
  fi
}

case "${1:-auto}" in
  up)   bring_up_ap ;;
  down) bring_down_ap ;;
  auto)
    say "NM state: $(nm_state); device $IFACE state: $(dev_state || echo '?')"
    if [[ "$(check_wifi_state)" == "connected" ]]; then
      say "Client Wi-Fi connected → ensure hotspot is down."
      bring_down_ap
      exit 0
    fi

    # Not connected; give client a grace window before enabling AP
    if wait_for_client; then
      say "Client Wi-Fi connected during grace period → ensure hotspot is down."
      bring_down_ap
    else
      say "Still not connected after grace → enable hotspot."
      bring_up_ap
    fi
    ;;
esac
