# Angular Dashboard Auto-start Service

A systemd service to automatically start the BFMC Dashboard Angular application on **Raspberry Pi 5** running Raspberry Pi OS (Bookworm).
The service ensures the dashboard starts automatically at boot and restarts if it crashes.

---

## Project structure

angular-autostart/  

├── install.sh # Installs the systemd service  

├── uninstall.sh # Removes all installed files  

├── config.env # Dashboard configuration  

├── start-dashboard.sh # Main script to start the dashboard  

└── angular-dashboard.service # systemd unit file  

## Features

- Automatically starts the Angular dashboard at boot
- Restarts the dashboard if it crashes
- Customizable configuration via config file
- Runs under the correct user permissions
- Includes proper logging and error handling

## Example workflow

1. Install the service:
```bash
cd angular-autostart
chmod +x install.sh
sudo ./install.sh
```

2. The dashboard will now start automatically at boot

3. Check the service status:
```bash
sudo systemctl status angular-dashboard.service
```

4. View logs:
```bash
journalctl -u angular-dashboard.service
```

## Installation (already installed in official image)

```bash
cd angular-autostart
chmod +x install.sh
sudo ./install.sh
```

## Uninstall

```bash
cd angular-autostart
chmod +x uninstall.sh
sudo ./uninstall.sh
```

## Customize dashboard configuration:

```bash
sudo nano /opt/angular-autostart/config.env
```

## Service management

Start the service:
```bash
sudo systemctl start angular-dashboard.service
```

Stop the service:
```bash
sudo systemctl stop angular-dashboard.service
```

Restart the service:
```bash
sudo systemctl restart angular-dashboard.service
```

Check service status:
```bash
sudo systemctl status angular-dashboard.service
```

View logs:
```bash
journalctl -u angular-dashboard.service
```