#!/bin/bash
set -euo pipefail

# Source configuration
source /opt/brain-autostart/config.env

# Logging helper
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /var/log/brain-monitor.log
}

# Check if brain process is running
is_brain_running() {
    pgrep -f "python.*main.py" > /dev/null 2>&1
}

# Check if dashboard is being accessed
is_dashboard_accessed() {
    log "Checking dashboard access on port ${DASHBOARD_PORT}..."
    local result
    result=$(netstat -an 2>/dev/null | grep ":${DASHBOARD_PORT}" | grep -c "ESTABLISHED" 2>/dev/null || echo 0)
    log "Dashboard ESTABLISHED connections count: $result"
    if [ "$result" -gt 0 ]; then
        log "Dashboard accessed!"
        return 0
    else
        log "Dashboard not accessed."
        return 1
    fi
}

# --- Main Loop ---
restart_count=0
last_restart=0

log "Starting brain monitor service..."

while true; do
    if is_dashboard_accessed; then
        if ! is_brain_running; then
            current_time=$(date +%s)

            # Reset counter if cooldown passed
            if [ $((current_time - last_restart)) -gt "$RESTART_COOLDOWN" ]; then
                restart_count=0
            fi

            if [ "$restart_count" -lt "$MAX_RESTART_ATTEMPTS" ]; then
                log "Dashboard accessed but brain not running. Launching brain..."
                /opt/brain-autostart/start-brain.sh
                last_restart=$current_time
                ((restart_count++))
                log "Restart attempt $restart_count of $MAX_RESTART_ATTEMPTS"
            else
                if [ $((current_time - last_restart)) -gt "$RESTART_COOLDOWN" ]; then
                    restart_count=0
                    log "Cooldown elapsed, resetting restart counter"
                else
                    log "Max restart attempts reached. Waiting for cooldown..."
                fi
            fi
        fi
    fi
    sleep "$CHECK_INTERVAL"
done
