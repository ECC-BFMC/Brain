#!/bin/bash
set -euo pipefail

# Source configuration
source /opt/angular-autostart/config.env

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /var/log/angular-dashboard.log
}

# Change to the dashboard directory
cd "$DASHBOARD_PATH"

# Ensure node_modules exists
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install
fi

# Start the dashboard
log "Starting Angular dashboard..."
export NODE_OPTIONS="$NODE_OPTIONS"
ng serve --host "$DASHBOARD_HOST" --port "$DASHBOARD_PORT" --disable-host-check