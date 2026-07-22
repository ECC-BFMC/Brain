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

    def handle_add(self, data):
        """Add a new WiFi network using the add-wifi.sh script."""
        try:
            ssid = data.get('ssid', '').strip()
            password = data.get('password', '').strip()

            if not ssid or not password:
                return jsonify({'success': False, 'error': 'SSID and password are required'}), 400

            script_path = os.path.join(
                self.repo_path, 'services', 'rpi-wifi-fallback', 'add-wifi.sh'
            )

            if not os.path.exists(script_path):
                return jsonify({'success': False, 'error': 'WiFi script not found'}), 500

            subprocess.Popen(
                ['sudo', script_path, ssid, password, 'yes'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            return jsonify({
                'success': True,
                'message': f'WiFi network "{ssid}" is being added. The car will attempt to connect. If the network is unavailable, it will fall back to the previous connection.'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

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

        fallback_script = os.path.join(
            self.repo_path, 'services', 'rpi-wifi-fallback', 'fallback.sh'
        )
        if os.path.exists(fallback_script):
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
