#!/bin/bash
set -euo pipefail

# Source configuration
source /opt/brain-autostart/config.env

# Logging helper
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /var/log/brain-monitor.log
}

log "start-brain.sh started"

cd "$BRAIN_PATH"

log "No existing brain found. Starting Python brain process..."
exec $PYTHON_ENV main.py >> /var/log/brain-monitor.log 2>&1
