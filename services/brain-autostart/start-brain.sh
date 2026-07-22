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

if [ ! -x "$PYTHON_ENV" ]; then
    log "Python virtual environment not found or not executable: $PYTHON_ENV"
    exit 1
fi

log "No existing brain found. Starting Python brain process..."
exec "$PYTHON_ENV" main.py >> /var/log/brain-monitor.log 2>&1
