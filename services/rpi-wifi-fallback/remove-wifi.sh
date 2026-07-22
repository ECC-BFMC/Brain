#!/bin/bash
set -euo pipefail

TARGET_NAME="${1:-}"
if [[ -z "$TARGET_NAME" ]]; then
  echo "Usage: $0 <connection-name>" >&2
  exit 2
fi

SCRIPT="$(realpath "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT")"
LOG="${LOG:-/var/log/rpi-wifi-fallback.log}"

run_as_root() {
  if (( EUID == 0 )); then
    "$@"
  else
    sudo -n "$@"
  fi
}

if [[ "${REMOVEWIFI_DETACHED:-0}" != "1" ]]; then
  UNIT="rpi-remove-wifi-$(date +%s)"
  run_as_root mkdir -p "$(dirname "$LOG")"
  run_as_root touch "$LOG"
  run_as_root chmod 0644 "$LOG"

  run_as_root systemd-run --unit "$UNIT" --collect \
    -p StandardOutput=append:"$LOG" \
    -p StandardError=append:"$LOG" \
    -p WorkingDirectory="$SCRIPT_DIR" \
    --setenv=REMOVEWIFI_DETACHED=1 \
    /bin/bash "$SCRIPT" "$TARGET_NAME"

  echo "[info] Scheduled removal of '$TARGET_NAME' in $UNIT"
  exit 0
fi

exec &> >(tee -a "$LOG")
say() { echo "[$(date +'%F %T')] $*"; }

# Give the HTTP response time to reach the browser before an active Wi-Fi drops.
sleep 2

was_active=0
if nmcli -t -f NAME connection show --active | grep -Fxq "$TARGET_NAME"; then
  was_active=1
fi

say "Removing Wi-Fi connection '$TARGET_NAME'."
if ! nmcli connection delete "$TARGET_NAME"; then
  say "Failed to remove Wi-Fi connection '$TARGET_NAME'."
  exit 1
fi

if (( was_active )); then
  fallback_script="$SCRIPT_DIR/fallback.sh"
  [[ -f "$fallback_script" ]] || fallback_script="/opt/rpi-wifi-fallback/fallback.sh"

  if [[ -f "$fallback_script" ]]; then
    say "Removed connection was active; starting the fallback hotspot."
    /bin/bash "$fallback_script" up
  else
    say "Fallback script not found; hotspot could not be started."
    exit 1
  fi
else
  say "Removed connection was inactive; leaving the current network unchanged."
fi
