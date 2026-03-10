#!/bin/bash
# kill-brain.sh - Kill all running main.py processes for user 'pi' and log actions

set -euo pipefail

LOGFILE="/var/log/brain-monitor.log"

count=0
# Use ps to get only main.py processes for pi with their PIDs
echo "Scanning for main.py processes owned by user pi..."
ps -u pi -o pid=,comm=,args= | grep 'python3 main.py' | while read -r pid comm args; do
    echo "Killing main.py process with PID $pid" | tee -a "$LOGFILE"
    kill "$pid"
    count=$((count+1))
done
if [ "$count" -eq 0 ]; then
    MSG="No main.py process found to kill."
    echo "$MSG" | tee -a "$LOGFILE"
else
    echo "Killed $count main.py process(es)." | tee -a "$LOGFILE"
fi
