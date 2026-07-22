import os
import subprocess
import threading
import time
from flask import jsonify


class WifiManager:
    """Handles WiFi network management via NetworkManager (nmcli)."""

    PROTECTED_CONNECTIONS = {'rpi-hotspot', 'preconfigured'}

    def __init__(self, repo_path):
        self.repo_path = repo_path

    def handle_list(self):
        """Get list of saved WiFi networks."""
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,TYPE', 'con', 'show'],
                capture_output=True, text=True, timeout=10
            )
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line and ':802-11-wireless' in line:
                    name = line.split(':')[0]
                    if name not in self.PROTECTED_CONNECTIONS:
                        networks.append({'name': name})
            return jsonify({'success': True, 'networks': networks})
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Command timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def _start_fallback(self):
        """Start the fallback hotspot without requiring an interactive sudo prompt."""
        fallback_script = os.path.join(
            self.repo_path, 'services', 'rpi-wifi-fallback', 'fallback.sh'
        )
        if not os.path.exists(fallback_script):
            return

        env = os.environ.copy()
        env.setdefault('LOG', '/tmp/rpi-wifi-fallback.log')
        env.setdefault('LOCK_FILE', '/tmp/rpi-wifi-fallback.lock')
        subprocess.Popen(
            ['/bin/bash', fallback_script, 'up'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    def _add_connection(self, ssid, password):
        """Create and activate a persistent NetworkManager WiFi profile."""
        # Let the HTTP response reach a client connected through the hotspot.
        time.sleep(2)

        def nmcli(*args, timeout=10):
            return subprocess.run(
                ['nmcli', *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        try:
            nmcli('radio', 'wifi', 'on')
            nmcli('device', 'set', 'wlan0', 'managed', 'yes')
            nmcli(
                'connection', 'modify', 'rpi-hotspot',
                'connection.autoconnect', 'no',
            )
            nmcli('connection', 'down', 'rpi-hotspot')
            nmcli('connection', 'delete', ssid)

            created = nmcli(
                'connection', 'add',
                'type', 'wifi',
                'ifname', 'wlan0',
                'con-name', ssid,
                'ssid', ssid,
            )
            if created.returncode != 0:
                self._start_fallback()
                return

            configured = nmcli(
                'connection', 'modify', ssid,
                'wifi-sec.key-mgmt', 'wpa-psk',
                'wifi-sec.psk', password,
                'wifi-sec.psk-flags', '0',
                '802-11-wireless.mode', 'infrastructure',
                '802-11-wireless.cloned-mac-address', 'permanent',
                'connection.permissions', '',
                'connection.autoconnect', 'yes',
                'connection.autoconnect-priority', '20',
            )
            if configured.returncode != 0:
                self._start_fallback()
                return

            connected = False
            for _ in range(3):
                nmcli('device', 'wifi', 'rescan', 'ifname', 'wlan0')
                result = nmcli(
                    '-w', '25', 'connection', 'up', ssid,
                    'ifname', 'wlan0',
                    timeout=30,
                )
                if result.returncode == 0:
                    connected = True
                    break

            if connected:
                nmcli('connection', 'delete', 'rpi-hotspot')
            else:
                self._start_fallback()
        except (OSError, subprocess.TimeoutExpired):
            self._start_fallback()

    def handle_add(self, data):
        """Schedule adding a WiFi profile without blocking the HTTP response."""
        ssid_value = data.get('ssid', '')
        password = data.get('password', '')
        ssid = ssid_value.strip() if isinstance(ssid_value, str) else ''

        if not ssid or not isinstance(password, str) or not password:
            return jsonify({'success': False, 'error': 'SSID and password are required'}), 400

        worker = threading.Thread(
            target=self._add_connection,
            args=(ssid, password),
            daemon=True,
        )
        worker.start()

        return jsonify({
            'success': True,
            'message': f'WiFi network "{ssid}" is being added. The car will attempt to connect and restore the hotspot if it cannot.'
        })

    def _remove_connection(self, name):
        """Remove a profile after the HTTP response has had time to leave."""
        time.sleep(2)

        active = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME', 'connection', 'show', '--active'],
            capture_output=True, text=True, timeout=10
        )
        active_names = set(active.stdout.strip().splitlines())
        was_active = name in active_names

        result = subprocess.run(
            ['nmcli', 'connection', 'delete', name],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 or not was_active:
            return

        self._start_fallback()

    def handle_remove(self, name):
        """Schedule removal of a saved WiFi network without blocking HTTP."""
        if not name:
            return jsonify({'success': False, 'error': 'Network name is required'}), 400

        if name in self.PROTECTED_CONNECTIONS:
            return jsonify({'success': False, 'error': 'Cannot remove this connection'}), 400

        worker = threading.Thread(
            target=self._remove_connection,
            args=(name,),
            daemon=True,
        )
        worker.start()

        return jsonify({
            'success': True,
            'message': (
                f'Network "{name}" is being removed. '
                'If it is active, the fallback hotspot will start shortly.'
            )
        })
