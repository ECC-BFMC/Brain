#!/bin/bash
# kill-brain.sh - Kill all running main.py processes for user 'pi' and log actions

set -euo pipefail

LOGFILE="/var/log/brain-monitor.log"

count=0
# Match the virtual-environment interpreter used by start-brain.sh.
echo "Scanning for .venv main.py processes owned by user pi..."
while read -r pid; do
    echo "Killing main.py process with PID $pid" | tee -a "$LOGFILE"
    kill "$pid"
    count=$((count+1))
done < <(pgrep -u pi -f '\.venv/bin/python([0-9.]*)? .*main\.py' || true)
if [ "$count" -eq 0 ]; then
    MSG="No main.py process found to kill."
    echo "$MSG" | tee -a "$LOGFILE"
else
    echo "Killed $count main.py process(es)." | tee -a "$LOGFILE"
fi
