# Brain Auto-start Service

A lightweight auto-start mechanism for **Raspberry Pi 5** running Raspberry Pi OS (Bookworm).  
It monitors Angular dashboard access and automatically starts the Python brain process when the dashboard is accessed. If the brain crashes, it can restart it.

---

## Project structure

brain-autostart/

├── install.sh # Installs the systemd service

├── uninstall.sh # Removes all installed files

├── kill-brain.sh # Kills all running brain processes

├── config.env # Brain configuration (ports, paths, etc.)

├── monitor-dashboard.sh # Script to monitor dashboard access

├── start-brain.sh # Script to start the Python brain process

└── brain-monitor.service # systemd unit file


## Features

- Monitors dashboard access on port 4200
- Automatically starts the Python backend when dashboard is accessed
- Prevents multiple brain instances
- Customizable configuration via config file
- Proper logging and error handling
- Resource-efficient monitoring

## Example workflow

1. Install the service:
```bash
cd brain-autostart
chmod +x install.sh
sudo ./install.sh
```

2. Open your browser and access the dashboard (e.g., http://raspberrypi.local:4200)
3. The service detects access and starts the brain automatically
4. Check the brain is running:
```bash
ps aux | grep main.py
```

5. View logs:
```bash
sudo tail -f /var/log/brain-monitor.log
```
---

## Customize brain configuration:

```bash
sudo nano /opt/brain-autostart/config.env
```

## Installation (already installed in official image)

```bash
cd brain-autostart
chmod +x install.sh
sudo ./install.sh
```

## Uninstall

```bash
cd brain-autostart
chmod +x uninstall.sh
sudo ./uninstall.sh
```

## Kill brain processes

If you need to stop the brain manually:

```bash
cd brain-autostart
chmod +x kill-brain.sh
./kill-brain.sh
```

## Service management

Start the service:
```bash
sudo systemctl start brain-monitor.service
```

Stop the service:
```bash
sudo systemctl stop brain-monitor.service
```

Restart the service:
```bash
sudo systemctl restart brain-monitor.service
```

Check service status:
```bash
sudo systemctl status brain-monitor.service
```

View logs:
```bash
sudo tail -f /var/log/brain-monitor.log
```

## Troubleshooting

If the brain doesn't start automatically:
1. Check the service logs: `sudo tail -f /var/log/brain-monitor.log`
2. Ensure the dashboard is accessible on port 4200
3. Verify Python environment is properly set up
4. Check if brain processes are already running: `ps aux | grep main.py`
5. Kill existing processes if needed: `./kill-brain.sh`