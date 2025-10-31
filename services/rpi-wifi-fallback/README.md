# Raspberry Pi Wi-Fi Fallback

A lightweight fallback mechanism for **Raspberry Pi 5** running Raspberry Pi OS (Bookworm).  
It tries to connect to saved Wi-Fi networks. If none are available, it automatically starts a Wi-Fi hotspot so you can connect, start the demo car and configure it for your home network via SSH.

---

## Project structure

rpi-wifi-fallback/

├── install.sh # Installs the systemd service

├── uninstall.sh # Removes all installed files

├── fallback.sh # Main script triggered at boot

├── add-wifi.sh # Script to add new Wi-Fi profiles

├── config.env # Hotspot SSID & password

└── rpi-wifi-fallback.service # systemd unit file


## Features

- Tries all saved Wi-Fi networks at boot using NetworkManager (default time, ~20 seconds)
- If none work, starts a Wi-Fi hotspot with static IP (192.168.50.1) or default naming (raspberrypi.local)
- Hotspot allows SSH/SFTP access to configure new networks and/or start the demo car
- Customizable hotspot data via config file
- Includes helper scripts to add Wi-Fi networks and prioritize connections

## Example workflow
1. Boot the Pi with no known networks nearby  
2. Connect your PC to the fallback hotspot  
   **SSID:** `BFMCDemoCar`  
   **Password:** `supersecurepassword`  
3. SSH into the Pi:
   ```bash
   ssh pi@192.168.50.1
   # or
   ssh pi@raspberrypi.local
   ```
4. Add your wifi network
```bash
sudo ./add-wifi.sh "MyHomeWiFi" "pass1234" yes
```
5. Reconnect your PC to Home Wi-Fi

## Customize hotspot credentials:

```bash
sudo nano /opt/rpi-wifi-fallback/config.env
```

## Installation (already installed in official image)

```bash
cd rpi-wifi-fallback
chmod +x install.sh
sudo ./install.sh
```

## Uninstall

```bash
cd rpi-wifi-fallback
chmod +x uninstall.sh
sudo ./uninstall.sh
```

## Add a new Wi-Fi network

When the Pi is acting as a hotspot, the Wi-Fi interface is occupied — so raspi-config won’t work.
Instead, use the provided helper script, providing the ssid, password, and if we want it to autoconnect to the network

```bash 
chmod +x add-wifi.sh
sudo ./add-wifi.sh "yourSSID" "yourPASSWORD" yes
```

## Networks handling:

View all saved Wi-Fi profiles

```bash 
ls -l /etc/NetworkManager/system-connections/
```

View or edit a specific connection

```bash
sudo nano /etc/NetworkManager/system-connections/HomeWiFi.nmconnection
```

Set the prioritization between networks (higher number = higher priority)

```bash 
sudo nmcli connection modify "HomeWiFi" connection.autoconnect-priority 10
```

## In case of missbehavior, check the service log:
```bash 
journalctl -u rpi-wifi-fallback.service
```
