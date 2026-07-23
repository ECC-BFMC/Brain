#!/bin/bash
set -euo pipefail

export LC_ALL=C

LOG="${LOG:-/var/log/rpi-wifi-fallback.log}"
mkdir -p "$(dirname "$LOG")"
touch "$LOG"
exec &> >(tee -a "$LOG")

CONFIG_FILE="${CONFIG_FILE:-/opt/rpi-wifi-fallback/config.env}"
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
CLIENT_CONNECT_TIMEOUT=${CLIENT_CONNECT_TIMEOUT:-30}

# Delete the AP profile on client connect? (true/false)
DELETE_AP_ON_CLIENT=${DELETE_AP_ON_CLIENT:-true}

NMCLI_BIN="${NMCLI_BIN:-nmcli}"
LOCK_FILE="${LOCK_FILE:-/run/rpi-wifi-fallback/operation.lock}"

run_nmcli() {
  "$NMCLI_BIN" "$@"
}
say() { echo "[$(date +'%F %T')] $*"; }

# single-instance lock
mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  say "Another instance is running; exiting."
  exit 0
fi

nm_state() { run_nmcli -t -f STATE g 2>/dev/null || echo unknown; }
dev_state() { run_nmcli -t -f GENERAL.STATE device show "$IFACE" 2>/dev/null | cut -d: -f2 || true; }

active_wifi_uuid() {
  run_nmcli -t --escape no -f UUID,TYPE,DEVICE connection show --active 2>/dev/null |
    awk -F: -v ifc="$IFACE" '($2=="802-11-wireless" || $2=="wifi") && $3==ifc {print $1; exit}'
}

client_wifi_connected() {
  local uuid mode
  uuid=$(active_wifi_uuid)
  [[ -n "$uuid" ]] || return 1
  mode=$(run_nmcli -g 802-11-wireless.mode connection show uuid "$uuid" 2>/dev/null || true)
  [[ "$mode" != "ap" ]]
}

wait_for_client() {
  local remaining=$GRACE_CONNECT_SECONDS
  say "Waiting up to ${GRACE_CONNECT_SECONDS}s for NetworkManager autoconnect..."
  while (( remaining-- > 0 )); do
    client_wifi_connected && return 0
    sleep 1
  done
  say "No client Wi-Fi came up during the grace period."
  return 1
}

saved_client_uuids() {
  run_nmcli -t --escape no -f UUID,TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY connection show 2>/dev/null |
    awk -F: '($2=="802-11-wireless" || $2=="wifi") && tolower($3)=="yes" {p=$4; if(p=="")p=0; print p "\t" $1}' |
    sort -k1,1nr -k2,2 |
    cut -f2
}

try_saved_clients() {
  local uuid profile_name attempted=0
  local -a saved_uuids=()

  say "Trying saved autoconnect Wi-Fi profiles on $IFACE..."
  run_nmcli radio wifi on || true
  run_nmcli device set "$IFACE" managed yes || true
  run_nmcli device set "$IFACE" autoconnect yes || true
  run_nmcli connection reload || true

  mapfile -t saved_uuids < <(saved_client_uuids)
  for uuid in "${saved_uuids[@]}"; do
    [[ -n "$uuid" ]] || continue
    if [[ "$(run_nmcli -g 802-11-wireless.mode connection show uuid "$uuid" 2>/dev/null || true)" == "ap" ]]; then
      continue
    fi

    attempted=1
    profile_name=$(run_nmcli -g connection.id connection show uuid "$uuid" 2>/dev/null || echo "$uuid")
    say "Activating saved Wi-Fi profile '$profile_name'..."
    if run_nmcli -w "$CLIENT_CONNECT_TIMEOUT" connection up uuid "$uuid" ifname "$IFACE" &&
        client_wifi_connected; then
      say "Connected using saved Wi-Fi profile '$profile_name'."
      return 0
    fi
    say "Saved Wi-Fi profile '$profile_name' did not connect."
  done

  (( attempted )) || say "No saved autoconnect Wi-Fi profiles found."
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

  # Target only our named hotspot. Never disconnect a client profile.
  if run_nmcli -t -f NAME connection show --active 2>/dev/null | grep -Fxq "$CON_NAME"; then
    say "Deactivating hotspot '$CON_NAME'."
    run_nmcli -w 10 connection down id "$CON_NAME" || true
  fi

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
    if client_wifi_connected; then
      say "Client Wi-Fi connected → ensure hotspot is down."
      bring_down_ap
      exit 0
    fi

    # Not connected; give client a grace window before enabling AP
    if wait_for_client; then
      say "Client Wi-Fi connected during grace period → ensure hotspot is down."
      bring_down_ap
    elif try_saved_clients; then
      say "Saved client Wi-Fi connected; ensure hotspot is down."
      bring_down_ap
    else
      say "No saved client Wi-Fi profile connected → enable hotspot."
      bring_up_ap
    fi
    ;;
esac
