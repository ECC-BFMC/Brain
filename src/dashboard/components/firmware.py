import json
import os
import time
import subprocess
import urllib.request
import urllib.error
import shutil
import glob as glob_module

from flask import jsonify


class FirmwareManager:
    """Handles Nucleo firmware check, download, and flash operations."""

    FIRMWARE_REPO = 'ECC-BFMC/Embedded_Platform'
    FIRMWARE_FILE_PATH = 'cmake_build/NUCLEO_F401RE/develop/GCC_ARM/robot_car.bin'
    FIRMWARE_API_URL = f'https://api.github.com/repos/{FIRMWARE_REPO}/commits'
    FIRMWARE_RAW_URL = f'https://raw.githubusercontent.com/{FIRMWARE_REPO}/master/{FIRMWARE_FILE_PATH}'
    NUCLEO_MOUNT_PATTERN = '/media/pi/NOD_F401RE*'

    def __init__(self, repo_path):
        self.repo_path = repo_path

    def _get_firmware_dir(self):
        return os.path.join(self.repo_path, 'src', 'hardware', 'firmware')

    def _get_local_info(self):
        """Read locally stored firmware version metadata."""
        info_path = os.path.join(self._get_firmware_dir(), 'firmware_version.json')
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                return json.load(f)
        return None

    def _save_local_info(self, info):
        """Save firmware version metadata to disk."""
        fw_dir = self._get_firmware_dir()
        os.makedirs(fw_dir, exist_ok=True)
        with open(os.path.join(fw_dir, 'firmware_version.json'), 'w') as f:
            json.dump(info, f, indent=2)

    def _find_nucleo_mount(self):
        """Find the Nucleo board's mass storage mount point."""
        matches = glob_module.glob(self.NUCLEO_MOUNT_PATTERN)
        for path in matches:
            if os.path.ismount(path):
                return path
        return None

    def handle_check(self):
        """Check if a newer firmware binary is available on the Embedded_Platform repo."""
        try:
            url = f'{self.FIRMWARE_API_URL}?path={self.FIRMWARE_FILE_PATH}&per_page=1'
            req = urllib.request.Request(url, headers={'User-Agent': 'BFMC-Brain'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                commits = json.loads(resp.read().decode())

            if not commits:
                return jsonify({'success': False, 'error': 'No commits found for firmware file'}), 500

            remote_sha = commits[0]['sha']
            remote_date = commits[0]['commit']['committer']['date']
            remote_message = commits[0]['commit']['message'].split('\n')[0]

            local_info = self._get_local_info()
            local_sha = local_info.get('commit_sha', '') if local_info else ''

            fw_path = os.path.join(self._get_firmware_dir(), 'robot_car.bin')
            has_local_file = os.path.exists(fw_path)

            update_available = (local_sha != remote_sha) or not has_local_file

            return jsonify({
                'success': True,
                'update_available': update_available,
                'has_local_file': has_local_file,
                'remote_sha': remote_sha[:7],
                'remote_date': remote_date,
                'remote_message': remote_message,
                'local_sha': local_sha[:7] if local_sha else '',
                'local_date': local_info.get('downloaded_at', '') if local_info else ''
            })
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to reach GitHub: {e.reason}'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_download(self):
        """Download the latest robot_car.bin from the Embedded_Platform repo."""
        try:
            url = f'{self.FIRMWARE_API_URL}?path={self.FIRMWARE_FILE_PATH}&per_page=1'
            req = urllib.request.Request(url, headers={'User-Agent': 'BFMC-Brain'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                commits = json.loads(resp.read().decode())

            if not commits:
                return jsonify({'success': False, 'error': 'No commits found for firmware file'}), 500

            remote_sha = commits[0]['sha']

            dl_req = urllib.request.Request(self.FIRMWARE_RAW_URL, headers={'User-Agent': 'BFMC-Brain'})
            with urllib.request.urlopen(dl_req, timeout=30) as resp:
                firmware_data = resp.read()

            fw_dir = self._get_firmware_dir()
            os.makedirs(fw_dir, exist_ok=True)
            fw_path = os.path.join(fw_dir, 'robot_car.bin')

            with open(fw_path, 'wb') as f:
                f.write(firmware_data)

            self._save_local_info({
                'commit_sha': remote_sha,
                'downloaded_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'file_size': len(firmware_data)
            })

            return jsonify({
                'success': True,
                'message': f'Firmware downloaded successfully ({len(firmware_data)} bytes). File saved to src/hardware/firmware/robot_car.bin'
            })
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to download firmware: {e.reason}'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_flash(self):
        """Flash robot_car.bin to the Nucleo board via its USB mass storage."""
        try:
            fw_path = os.path.join(self._get_firmware_dir(), 'robot_car.bin')
            if not os.path.exists(fw_path):
                return jsonify({
                    'success': False,
                    'error': 'Firmware file not found. Download it first.'
                }), 400

            fw_size = os.path.getsize(fw_path)
            if fw_size == 0:
                return jsonify({
                    'success': False,
                    'error': 'Firmware file is empty. Try downloading again.'
                }), 400

            nucleo_mount = self._find_nucleo_mount()
            if not nucleo_mount:
                return jsonify({
                    'success': False,
                    'error': 'Nucleo board not detected. Make sure it is connected via USB and mounted.'
                }), 404

            if not os.access(nucleo_mount, os.W_OK):
                return jsonify({
                    'success': False,
                    'error': f'Cannot write to Nucleo mount point ({nucleo_mount}). Check permissions.'
                }), 403

            dest_path = os.path.join(nucleo_mount, 'robot_car.bin')
            shutil.copy2(fw_path, dest_path)

            subprocess.run(['sync'], timeout=10)

            return jsonify({
                'success': True,
                'message': f'Firmware flashed successfully to {nucleo_mount}. The Nucleo will reset automatically.'
            })
        except PermissionError:
            return jsonify({'success': False, 'error': 'Permission denied writing to Nucleo. Try running with sudo.'}), 403
        except OSError as e:
            return jsonify({'success': False, 'error': f'Failed to flash firmware: {e}'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
