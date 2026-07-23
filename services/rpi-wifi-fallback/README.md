# Raspberry Pi Wi-Fi management and fallback

This service targets Raspberry Pi OS Bookworm with NetworkManager. It provides:

- dashboard-managed persistent WPA/WPA2-PSK client profiles;
- a fallback access point when no saved client profile can connect;
- NetworkManager dispatcher recovery after a client connection drops;
- a shared lock that prevents the dashboard, manual helper, and fallback service from changing `wlan0` concurrently;
- a narrowly scoped Polkit rule for the non-root `brain-monitor.service`.

## Installation and updates

Run the installer after copying or pulling this repository onto the Raspberry Pi. A Git update alone does not update files already installed under `/opt` and `/etc`.

```bash
cd ~/Documents/Brain/services/rpi-wifi-fallback
bash install.sh
sudo reboot
```

When started as the regular `pi` user, the installer requests sudo
authentication once before making changes. `sudo bash install.sh` is also
supported. Run it from an interactive SSH or local terminal, not from the
dashboard service.

The installer deploys:

- `/opt/rpi-wifi-fallback/{fallback.sh,add-wifi.sh,config.env}`;
- `/etc/systemd/system/wifi-fallback.service`;
- `/etc/NetworkManager/dispatcher.d/90-wifi-fallback`;
- `/etc/polkit-1/rules.d/49-brain-networkmanager.rules`;
- `/etc/systemd/system/brain-monitor.service.d/20-wifi-security.conf`;
- `/etc/tmpfiles.d/rpi-wifi-fallback.conf`.

The installer creates the system group `brain-network`, adds `pi`, and injects
the group explicitly into `brain-monitor.service` with `SupplementaryGroups`.
The scoped Polkit rule authorizes NetworkManager mutations only for user `pi`
in that group. The drop-in also enables `NoNewPrivileges`.

The dispatcher-started root service waits up to 30 seconds for an in-progress
dashboard Wi-Fi operation to release the shared lock. This prevents a
disconnect event from being lost while an active profile is being removed.

## Configuration

Edit the installed configuration:

```bash
sudo nano /opt/rpi-wifi-fallback/config.env
sudo systemctl restart wifi-fallback.service
```

Important settings:

- `IFACE`: wireless interface, normally `wlan0`;
- `SSID` and `PASSWORD`: fallback hotspot credentials;
- `CON_NAME`: NetworkManager connection name for the hotspot;
- `GRACE_CONNECT_SECONDS`: boot/disconnect grace period;
- `CLIENT_CONNECT_TIMEOUT`: timeout for each saved client profile;
- `DELETE_AP_ON_CLIENT`: delete the hotspot profile after a client connects.

The Raspberry Pi wireless country must also be configured.

## Dashboard behavior

Adding a network first creates and validates an inactive candidate profile while the hotspot is still available. The API returns only after that succeeds. It then:

1. waits briefly for the HTTP response to reach the browser;
2. stops the hotspot;
3. attempts the candidate profile up to three times;
4. replaces an older profile for the same SSID only after successful activation;
5. restores the previous client profile or fallback hotspot on failure.

Deleting an inactive profile is synchronous. Deleting the active profile returns an operation ID, disconnects it after the HTTP response, and starts the fallback hotspot.

The dashboard stores the current operation ID in browser storage, so reopening Settings can recover its final status while the Python process remains running.

## Manual helper

When the dashboard is unavailable:

```bash
sudo /opt/rpi-wifi-fallback/add-wifi.sh "MyHomeWiFi" "pass1234" yes
```

The helper and dashboard use the same runtime lock. Do not run raw `nmcli` profile mutations at the same time.

## Raspberry Pi verification

Check installation and authorization:

```bash
systemctl cat brain-monitor.service wifi-fallback.service
systemctl is-active NetworkManager polkit
systemctl show brain-monitor.service -p MainPID -p NoNewPrivileges -p SupplementaryGroups
id pi
sudo cat /etc/polkit-1/rules.d/49-brain-networkmanager.rules
sudo ls -l /run/rpi-wifi-fallback/operation.lock
nmcli general permissions
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
```

Follow logs during a dashboard operation:

```bash
sudo journalctl -f \
  -u brain-monitor.service \
  -u wifi-fallback.service \
  -u NetworkManager \
  -u polkit
```

Recommended test matrix:

1. Boot with no known network and verify the fallback hotspot appears.
2. Add a valid nearby WPA/WPA2 network from the dashboard.
3. Reconnect the browser device to that network and verify the profile is marked connected.
4. Reboot and verify NetworkManager autoconnects.
5. Add the same SSID with a wrong password and verify the old profile is restored.
6. Delete an inactive profile and verify it disappears immediately.
7. Delete the active profile and verify the fallback hotspot returns.
8. Move out of range of the client AP and verify the dispatcher starts fallback reconciliation.

## Uninstall

```bash
cd ~/Documents/Brain/services/rpi-wifi-fallback
sudo ./uninstall.sh
sudo reboot
```
