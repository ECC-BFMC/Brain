# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC orginazers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "../../..")

import queue
import psutil
import json
import inspect
import eventlet
import os
import time
import subprocess
import urllib.request
import hashlib
import shutil
import glob

from flask import Flask, request
from flask_socketio import SocketIO
from flask_cors import CORS
from enum import Enum

from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.templates.workerprocess import WorkerProcess
from src.utils.messages.allMessages import Semaphores
from src.statemachine.stateMachine import StateMachine
from src.dashboard.components.calibration import Calibration

import src.utils.messages.allMessages as allMessages


class processDashboard(WorkerProcess):
    """This process handles the dashboard interactions, updating the UI based on the system's state.
    
    Args:
        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.
        logging (logging object): Made for debugging.
        debugging (bool): Enable debugging mode.
    """
    # ====================================== INIT ==========================================
    def __init__(self, queueList, logging, ready_event=None, debugging = False):

        self.running = True
        self.queueList = queueList
        self.logger = logging
        self.debugging = debugging

        # state machine
        self.stateMachine = StateMachine.get_instance()

        # message handling
        self.messages = {}
        self.sendMessages = {}
        self.messagesAndVals = {}

        # hardware monitoring
        self.memoryUsage = 0
        self.cpuCoreUsage = 0
        self.cpuTemperature = 0


        # heartbeat
        self.heartbeat_last_sent = time.time()
        self.heartbeat_retries = 0
        self.heartbeat_max_retries = 3
        self.heartbeat_time_between_heartbeats = 20 # seconds
        self.heartbeat_time_between_retries = 5 # seconds # put a higher value if the connection is not stable (e.g. 5 seconds)
        self.heartbeat_received = False

        # session management
        self.sessionActive = False
        self.activeUser = None

        # serial connection state
        self.serialConnected = False

        # configuration
        self.table_state_file = self._get_table_state_path()

        # setup flask and socketio
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        CORS(self.app, supports_credentials=True)

        # calibration
        self.calibration = Calibration(self.queueList, self.socketio)

        # initialize message handling
        self._initialize_messages()
        self._setup_websocket_handlers()
        self._setup_rest_routes()
        self._start_background_tasks()

        super(processDashboard, self).__init__(self.queueList, ready_event)
    

    def _get_table_state_path(self):
        """Get the path for table state file."""
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, 'src', 'utils', 'table_state.json')
    

    def _initialize_messages(self):
        """Initialize message handling systems."""
        self.get_name_and_vals()
        self.messagesAndVals.pop("mainCamera", None)
        self.messagesAndVals.pop("Semaphores", None)
        self.subscribe()
    

    def _setup_websocket_handlers(self):
        """Setup WebSocket event handlers."""
        self.socketio.on_event('message', self.handle_message)
        self.socketio.on_event('save', self.handle_save_table_state)
        self.socketio.on_event('load', self.handle_load_table_state)


    def _setup_rest_routes(self):
        """Setup REST API routes for request/response operations."""
        from flask import request as flask_request, jsonify
        
        # WiFi Management
        @self.app.route('/api/wifi', methods=['GET'])
        def api_get_wifi_list():
            """Get list of saved WiFi networks."""
            return self._handle_wifi_list()
        
        @self.app.route('/api/wifi', methods=['POST'])
        def api_add_wifi():
            """Add a new WiFi network."""
            data = flask_request.get_json()
            return self._handle_wifi_add(data)
        
        @self.app.route('/api/wifi/<name>', methods=['DELETE'])
        def api_remove_wifi(name):
            """Remove a WiFi network."""
            return self._handle_wifi_remove(name)
        
        # Table State Management
        @self.app.route('/api/table', methods=['GET'])
        def api_load_table():
            """Load table state from file."""
            try:
                with open(self.table_state_file, 'r') as json_file:
                    data = json.load(json_file)
                return jsonify({'success': True, 'data': data})
            except FileNotFoundError:
                return jsonify({'success': False, 'error': 'No saved table state found'}), 404
            except json.JSONDecodeError:
                return jsonify({'success': False, 'error': 'Invalid JSON in saved file'}), 500
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/table', methods=['POST'])
        def api_save_table():
            """Save table state to file."""
            try:
                data = flask_request.get_json()
                os.makedirs(os.path.dirname(self.table_state_file), exist_ok=True)
                with open(self.table_state_file, 'w') as json_file:
                    json.dump(data, json_file, indent=4)
                return jsonify({'success': True, 'message': 'Table state saved'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Serial Connection Status
        @self.app.route('/api/serial/status', methods=['GET'])
        def api_serial_status():
            """Get current serial connection state."""
            return jsonify({'success': True, 'connected': self.serialConnected})
        
        # Codebase Update Management
        @self.app.route('/api/update/check', methods=['GET'])
        def api_check_updates():
            """Check if there are updates available on the remote repository."""
            return self._handle_check_updates()
        
        @self.app.route('/api/update/pull', methods=['POST'])
        def api_pull_updates():
            """Pull the latest updates from the remote repository."""
            return self._handle_pull_updates()
        
        # Firmware Update Management
        @self.app.route('/api/firmware/check', methods=['GET'])
        def api_check_firmware():
            """Check if a new firmware binary is available."""
            return self._handle_check_firmware()
        
        @self.app.route('/api/firmware/download', methods=['POST'])
        def api_download_firmware():
            """Download the latest firmware binary."""
            return self._handle_download_firmware()
        
        @self.app.route('/api/firmware/flash', methods=['POST'])
        def api_flash_firmware():
            """Flash the firmware binary to the Nucleo board."""
            return self._handle_flash_firmware()


    def _handle_wifi_list(self):
        """Get list of saved WiFi networks."""
        from flask import jsonify
        
        # Protected connections that shouldn't be shown or deleted
        # Add any preconfigured connection names here
        protected_connections = {'rpi-hotspot', 'preconfigured'}  # TODO: Update 'preconfigured' with actual name
        
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,TYPE', 'con', 'show'],
                capture_output=True, text=True, timeout=10
            )
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line and ':802-11-wireless' in line:
                    name = line.split(':')[0]
                    # Skip protected connections
                    if name not in protected_connections:
                        networks.append({'name': name})
            return jsonify({'success': True, 'networks': networks})
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Command timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    def _handle_wifi_add(self, data):
        """Add a new WiFi network using the add-wifi.sh script."""
        from flask import jsonify
        try:
            ssid = data.get('ssid', '').strip()
            password = data.get('password', '').strip()
            
            if not ssid or not password:
                return jsonify({'success': False, 'error': 'SSID and password are required'}), 400
            
            # Get the path to the add-wifi.sh script
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'services', 'rpi-wifi-fallback', 'add-wifi.sh'
            )
            
            if not os.path.exists(script_path):
                return jsonify({'success': False, 'error': 'WiFi script not found'}), 500
            
            # Run the script asynchronously (it detaches itself)
            # The script handles the connection attempt and fallback
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


    def _handle_wifi_remove(self, name):
        """Remove a saved WiFi network."""
        from flask import jsonify
        
        # Protected connections that shouldn't be deleted
        protected_connections = {'rpi-hotspot', 'preconfigured'}  # TODO: Update 'preconfigured' with actual name
        
        try:
            if not name:
                return jsonify({'success': False, 'error': 'Network name is required'}), 400
            
            # Don't allow removing protected connections
            if name in protected_connections:
                return jsonify({'success': False, 'error': 'Cannot remove this connection'}), 400
            
            result = subprocess.run(
                ['sudo', 'nmcli', 'connection', 'delete', name],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                # After successful deletion, use fallback.sh to activate the hotspot
                fallback_script = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    'services', 'rpi-wifi-fallback', 'fallback.sh'
                )
                if os.path.exists(fallback_script):
                    subprocess.Popen(
                        ['sudo', fallback_script, 'up'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                return jsonify({'success': True, 'message': f'Network "{name}" removed. Hotspot activated.'})
            else:
                return jsonify({'success': False, 'error': result.stderr or 'Failed to remove network'}), 500
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Command timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    # Official BFMC Brain repository - all updates come from here
    OFFICIAL_REPO_URL = 'https://github.com/ECC-BFMC/Brain.git'
    OFFICIAL_REMOTE_NAME = 'bfmc-official'

    # Embedded Platform firmware
    FIRMWARE_REPO = 'ECC-BFMC/Embedded_Platform'
    FIRMWARE_FILE_PATH = 'cmake_build/NUCLEO_F401RE/develop/GCC_ARM/robot_car.bin'
    FIRMWARE_API_URL = f'https://api.github.com/repos/{FIRMWARE_REPO}/commits'
    FIRMWARE_RAW_URL = f'https://raw.githubusercontent.com/{FIRMWARE_REPO}/master/{FIRMWARE_FILE_PATH}'

    def _validate_repo(self, repo_path):
        """Validate that this is an official clone and on master branch.
        
        Returns (is_valid, error_message, details_dict).
        """
        details = {'is_official_clone': False, 'valid_branch': False, 'branch': ''}

        # Check if origin remote points to the official ECC-BFMC/Brain repo
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_path,
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, 'No origin remote found. Only clones from the official ECC-BFMC/Brain repository can be updated from here.', details

        origin_url = result.stdout.strip().lower()
        official_patterns = ['ecc-bfmc/brain.git', 'ecc-bfmc/brain']
        if not any(pat in origin_url for pat in official_patterns):
            return False, 'This repository was not cloned from the official ECC-BFMC/Brain repository. Only official clones can be updated from here.', details

        details['is_official_clone'] = True

        # Check current branch is master
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path,
            capture_output=True, text=True, timeout=10
        )
        current_branch = branch_result.stdout.strip()
        details['branch'] = current_branch

        if current_branch not in ('main', 'master'):
            return False, f'Updates are only available on the master branch. You are currently on "{current_branch}".', details

        details['valid_branch'] = True
        return True, '', details

    def _ensure_official_remote(self, repo_path):
        """Ensure the official BFMC remote is configured for updates."""
        result = subprocess.run(
            ['git', 'remote', 'get-url', self.OFFICIAL_REMOTE_NAME],
            cwd=repo_path,
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            subprocess.run(
                ['git', 'remote', 'add', self.OFFICIAL_REMOTE_NAME, self.OFFICIAL_REPO_URL],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
        else:
            current_url = result.stdout.strip()
            if current_url != self.OFFICIAL_REPO_URL:
                subprocess.run(
                    ['git', 'remote', 'set-url', self.OFFICIAL_REMOTE_NAME, self.OFFICIAL_REPO_URL],
                    cwd=repo_path,
                    capture_output=True, text=True, timeout=10
                )
        
        return self.OFFICIAL_REMOTE_NAME

    def _handle_check_updates(self):
        """Check if there are updates available from the official BFMC repository."""
        from flask import jsonify
        try:
            repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            is_valid, validation_msg, details = self._validate_repo(repo_path)
            if not is_valid:
                return jsonify({
                    'success': True,
                    'update_available': False,
                    'is_official_clone': details['is_official_clone'],
                    'valid_branch': details['valid_branch'],
                    'branch': details.get('branch', ''),
                    'validation_error': validation_msg
                })
            
            update_remote = self._ensure_official_remote(repo_path)
            
            fetch_result = subprocess.run(
                ['git', 'fetch', update_remote],
                cwd=repo_path,
                capture_output=True, text=True, timeout=30
            )
            
            if fetch_result.returncode != 0:
                return jsonify({'success': False, 'error': 'Failed to fetch from official repository'}), 500
            
            current_branch = details['branch']
            
            current_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
            current_commit = current_result.stdout.strip()
            current_commit_short = current_commit[:7] if current_commit else ''
            
            remote_branch = f'{update_remote}/master'
            check_result = subprocess.run(
                ['git', 'rev-parse', remote_branch],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
            
            if check_result.returncode != 0:
                return jsonify({
                    'success': True,
                    'current_commit': current_commit,
                    'current_commit_short': current_commit_short,
                    'remote_commit': '',
                    'remote_commit_short': '',
                    'update_available': False,
                    'is_official_clone': True,
                    'valid_branch': True,
                    'branch': current_branch,
                    'remote': 'ECC-BFMC/Brain',
                    'message': 'Could not reach official repository'
                })
            
            remote_commit = check_result.stdout.strip()
            remote_commit_short = remote_commit[:7] if remote_commit else ''
            
            merge_base_result = subprocess.run(
                ['git', 'merge-base', 'HEAD', remote_branch],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
            merge_base = merge_base_result.stdout.strip()
            
            update_available = merge_base == current_commit and remote_commit != current_commit
            
            return jsonify({
                'success': True,
                'current_commit': current_commit,
                'current_commit_short': current_commit_short,
                'remote_commit': remote_commit,
                'remote_commit_short': remote_commit_short,
                'update_available': update_available,
                'is_official_clone': True,
                'valid_branch': True,
                'branch': current_branch,
                'remote': 'ECC-BFMC/Brain',
                'remote_branch': 'master'
            })
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Command timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    def _handle_pull_updates(self):
        """Pull the latest updates from the official BFMC repository."""
        from flask import jsonify
        try:
            repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            is_valid, validation_msg, details = self._validate_repo(repo_path)
            if not is_valid:
                return jsonify({'success': False, 'error': validation_msg}), 403
            
            update_remote = self._ensure_official_remote(repo_path)
            remote_branch = 'master'
            
            # Stash any local changes
            stash_result = subprocess.run(
                ['git', 'stash'],
                cwd=repo_path,
                capture_output=True, text=True, timeout=10
            )
            had_stash = 'No local changes' not in stash_result.stdout
            
            # Fetch latest from official repository
            fetch_result = subprocess.run(
                ['git', 'fetch', update_remote],
                cwd=repo_path,
                capture_output=True, text=True, timeout=30
            )
            
            if fetch_result.returncode != 0:
                if had_stash:
                    subprocess.run(
                        ['git', 'stash', 'pop'],
                        cwd=repo_path,
                        capture_output=True, text=True, timeout=10
                    )
                return jsonify({
                    'success': False,
                    'error': 'Failed to fetch from official repository'
                }), 500
            
            # Merge the updates from the official BFMC master branch
            merge_result = subprocess.run(
                ['git', 'merge', f'{update_remote}/{remote_branch}', '--no-edit'],
                cwd=repo_path,
                capture_output=True, text=True, timeout=60
            )
            
            if merge_result.returncode != 0:
                # Abort the merge and restore state
                subprocess.run(
                    ['git', 'merge', '--abort'],
                    cwd=repo_path,
                    capture_output=True, text=True, timeout=10
                )
                if had_stash:
                    subprocess.run(
                        ['git', 'stash', 'pop'],
                        cwd=repo_path,
                        capture_output=True, text=True, timeout=10
                    )
                return jsonify({
                    'success': False,
                    'error': 'Merge conflict detected. Please resolve manually or contact support.'
                }), 500
            
            # Restore stashed changes if there were any
            if had_stash:
                pop_result = subprocess.run(
                    ['git', 'stash', 'pop'],
                    cwd=repo_path,
                    capture_output=True, text=True, timeout=10
                )
                if pop_result.returncode != 0:
                    return jsonify({
                        'success': True,
                        'message': 'Update from ECC-BFMC/Brain successful! Note: Could not restore local changes automatically. Run "git stash pop" manually if needed. Please restart the application.'
                    })
            
            return jsonify({
                'success': True,
                'message': 'Update from ECC-BFMC/Brain successful! Please restart the application for changes to take effect.'
            })
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Update timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    def _get_firmware_dir(self):
        """Get the local firmware storage directory."""
        repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(repo_path, 'src', 'hardware', 'firmware')

    def _get_local_firmware_info(self):
        """Read locally stored firmware version metadata."""
        info_path = os.path.join(self._get_firmware_dir(), 'firmware_version.json')
        if os.path.exists(info_path):
            with open(info_path, 'r') as f:
                return json.load(f)
        return None

    def _save_local_firmware_info(self, info):
        """Save firmware version metadata to disk."""
        fw_dir = self._get_firmware_dir()
        os.makedirs(fw_dir, exist_ok=True)
        with open(os.path.join(fw_dir, 'firmware_version.json'), 'w') as f:
            json.dump(info, f, indent=2)

    def _handle_check_firmware(self):
        """Check if a newer firmware binary is available on the Embedded_Platform repo."""
        from flask import jsonify
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

            local_info = self._get_local_firmware_info()
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

    def _handle_download_firmware(self):
        """Download the latest robot_car.bin from the Embedded_Platform repo."""
        from flask import jsonify
        try:
            # Get the latest commit SHA first
            url = f'{self.FIRMWARE_API_URL}?path={self.FIRMWARE_FILE_PATH}&per_page=1'
            req = urllib.request.Request(url, headers={'User-Agent': 'BFMC-Brain'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                commits = json.loads(resp.read().decode())

            if not commits:
                return jsonify({'success': False, 'error': 'No commits found for firmware file'}), 500

            remote_sha = commits[0]['sha']

            # Download the binary
            dl_req = urllib.request.Request(self.FIRMWARE_RAW_URL, headers={'User-Agent': 'BFMC-Brain'})
            with urllib.request.urlopen(dl_req, timeout=30) as resp:
                firmware_data = resp.read()

            fw_dir = self._get_firmware_dir()
            os.makedirs(fw_dir, exist_ok=True)
            fw_path = os.path.join(fw_dir, 'robot_car.bin')

            with open(fw_path, 'wb') as f:
                f.write(firmware_data)

            self._save_local_firmware_info({
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

    NUCLEO_MOUNT_PATTERN = '/media/pi/NOD_F401RE*'

    def _find_nucleo_mount(self):
        """Find the Nucleo board's mass storage mount point."""
        matches = glob.glob(self.NUCLEO_MOUNT_PATTERN)
        for path in matches:
            if os.path.ismount(path):
                return path
        return None

    def _handle_flash_firmware(self):
        """Flash robot_car.bin to the Nucleo board via its USB mass storage."""
        from flask import jsonify
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


    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        psutil.cpu_percent(interval=1, percpu=False) # warm up

        eventlet.spawn(self.update_hardware_data)
        eventlet.spawn(self.send_continuous_messages)
        eventlet.spawn(self.send_hardware_data_to_frontend)
        eventlet.spawn(self.send_heartbeat)
        eventlet.spawn(self.stream_console_logs)

    def stream_console_logs(self):
        """Monitor the Log queue and emit messages to frontend."""
        log_queue = self.queueList.get("Log")
        if not log_queue:
            return

        while self.running:
            try:
                while not log_queue.empty():
                    msg = log_queue.get_nowait()
                    self.socketio.emit('console_log', {'data': msg})
                    eventlet.sleep(0)
                
                eventlet.sleep(0.1)
            except queue.Empty:
                eventlet.sleep(0.1)
            except Exception as e:
                if self.debugging:
                    self.logger.error(f"Error streaming logs: {e}")
                eventlet.sleep(1)


    # ===================================== STOP ==========================================
    def stop(self):
        """Stop the dashboard process."""
        super(processDashboard, self).stop()
        self.running = False


    # ===================================== RUN ==========================================
    def run(self):
        """Apply the initializing method."""
        if self.ready_event:
            self.ready_event.set()

        self.socketio.run(self.app, host='0.0.0.0', port=5005)


    def subscribe(self):
        """Subscribe function. In this function we make all the required subscribe to process gateway."""
        for name, enum in self.messagesAndVals.items():
            if enum["owner"] != "Dashboard":
                subscriber = messageHandlerSubscriber(self.queueList, enum["enum"], "lastOnly", True)
                self.messages[name] = {"obj": subscriber}
            else:
                sender = messageHandlerSender(self.queueList, enum["enum"])
                self.sendMessages[str(name)] = {"obj": sender}

        subscriber = messageHandlerSubscriber(self.queueList, Semaphores, "fifo", True)
        self.messages["Semaphores"] = {"obj": subscriber}


    def get_name_and_vals(self):
        """Extract all message names and values for processing."""
        classes = inspect.getmembers(allMessages, inspect.isclass)
        for name, cls in classes:
            if name != "Enum" and issubclass(cls, Enum):
                self.messagesAndVals[name] = {"enum": cls, "owner": cls.Owner.value} # type: ignore


    def send_message_to_brain(self, dataName, dataDict):
        """Send messages to the backend."""
        if dataName in self.sendMessages:
            self.sendMessages[dataName]["obj"].send(dataDict.get("Value"))


    def handle_message(self, data):
        """Handle incoming WebSocket messages."""
        if self.debugging:
            self.logger.info("Received message: " + str(data))

        try:
            dataDict = json.loads(data)
            dataName = dataDict["Name"]
            socketId = request.sid

            if dataName == "SessionAccess":
                self.handle_single_user_session(socketId)
            elif self.sessionActive and self.activeUser != socketId:
                print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;93mWARNING\033[0m - Message received from unauthorized user \033[94m{socketId}\033[0m")
                return

            if dataName == "Heartbeat":
                self.handle_heartbeat()
            elif dataName == "SessionEnd":
                self.handle_session_end(socketId)
            elif dataName == "DrivingMode":
                self.handle_driving_mode(dataDict)
            elif dataName == "Calibration":
                self.handle_calibration(dataDict, socketId)
            elif dataName == "GetCurrentSerialConnectionState":
                self.handle_get_current_serial_connection_state(socketId)
            else:
                self.send_message_to_brain(dataName, dataDict)

            self.socketio.emit('response', {'data': 'Message received: ' + str(data)}, room=socketId) # type: ignore
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON message: {e}")
            self.socketio.emit('response', {'error': 'Invalid JSON format'}, room=socketId) # type: ignore


    def handle_heartbeat(self):
        """Handle heartbeat message."""
        self.heartbeat_retries = 0
        self.heartbeat_last_sent = time.time()
        self.heartbeat_received = True


    def handle_driving_mode(self, dataDict):
        """Handle driving mode change."""
        self.stateMachine.request_mode(f"dashboard_{dataDict['Value']}_button")


    def handle_calibration(self, dataDict, socketId):
        """Handle calibration signals from frontend."""
        self.calibration.handle_calibration_signal(dataDict, socketId)


    def handle_get_current_serial_connection_state(self, socketId):
        """Handle getting the current serial connection state."""
        self.socketio.emit('current_serial_connection_state', {'data': self.serialConnected}, room=socketId)


    def handle_single_user_session(self, socketId):
        """Handle session access for a single user."""
        if not self.sessionActive:
            self.sessionActive = True
            self.activeUser = socketId
            print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;92mINFO\033[0m - Session access granted to \033[94m{socketId}\033[0m")
            self.socketio.emit('session_access', {'data': True}, room=socketId)
            self.send_message_to_brain("RequestSteerLimits", {"Value": True})
        elif self.activeUser == socketId:
            self.socketio.emit('session_access', {'data': True}, room=socketId)
            self.send_message_to_brain("RequestSteerLimits", {"Value": True})
        else:
            print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;92mINFO\033[0m - Session access denied to \033[94m{socketId}\033[0m")
            self.socketio.emit('session_access', {'data': False}, room=socketId)


    def handle_session_end(self, socketId):
        """Handle session end for the single user."""
        if self.sessionActive and self.activeUser == socketId:
            self.sessionActive = False
            self.activeUser = None


    def handle_save_table_state(self, data):
        """Handle saving the table state to a JSON file."""
        if self.debugging:
            self.logger.info("Received save message: " + data)

        try:
            dataDict = json.loads(data)
            os.makedirs(os.path.dirname(self.table_state_file), exist_ok=True)
            
            with open(self.table_state_file, 'w') as json_file:
                json.dump(dataDict, json_file, indent=4)
                
            self.socketio.emit('response', {'data': 'Table state saved successfully'})
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON for save: {e}")
            self.socketio.emit('response', {'error': 'Invalid JSON format'})
        except OSError as e:
            self.logger.error(f"Failed to save table state: {e}")
            self.socketio.emit('response', {'error': 'Failed to save table state'})


    def handle_load_table_state(self, data):
        """Handle loading the table state from a JSON file."""
        try:
            with open(self.table_state_file, 'r') as json_file:
                dataDict = json.load(json_file)
            self.socketio.emit('loadBack', {'data': dataDict})
        except FileNotFoundError:
            self.socketio.emit('response', {'error': 'File not found. Please save the table state first.'})
        except json.JSONDecodeError:
            self.socketio.emit('response', {'error': 'Failed to parse JSON data from the file.'})
        except OSError as e:
            self.logger.error(f"Failed to load table state: {e}")
            self.socketio.emit('response', {'error': 'Failed to load table state'})


    def update_hardware_data(self):
        """Monitor and update hardware metrics periodically."""
        self.cpuCoreUsage = psutil.cpu_percent(interval=None, percpu=False)
        self.memoryUsage = psutil.virtual_memory().percent
        self.cpuTemperature = round(psutil.sensors_temperatures()['cpu_thermal'][0].current)

        eventlet.spawn_after(1, self.update_hardware_data)


    def send_heartbeat(self):
        """Send a heartbeat message to the frontend."""
        if not self.running:
            return

        if not self.heartbeat_received and self.sessionActive:
            self.heartbeat_retries += 1
            if self.heartbeat_retries < self.heartbeat_max_retries:
                self.socketio.emit('heartbeat', {'data': 'Heartbeat'})
            else:
                print(f"\033[1;97m[ Dashboard ] :\033[0m \033[1;93mWARNING\033[0m - Connection lost with peer \033[94m{self.activeUser}\033[0m")
                self.socketio.emit('heartbeat_disconnect', {'data': 'Heartbeat timeout'})
                self.sessionActive = False
                self.activeUser = None
                self.heartbeat_retries = 0

            eventlet.spawn_after(self.heartbeat_time_between_retries, self.send_heartbeat)
        else:
            self.heartbeat_received = False
            eventlet.spawn_after(self.heartbeat_time_between_heartbeats, self.send_heartbeat)


    def send_continuous_messages(self):
        """Process and send subscriber messages to the frontend."""
        if not self.running:
            return

        for msg, subscriber in self.messages.items():
            resp = subscriber["obj"].receive()
            if resp is not None:
                if msg == "SerialConnectionState":
                    self.serialConnected = resp

                self.socketio.emit(msg, {"value": resp})
                if self.debugging:
                    self.logger.info(f"{msg}: {resp}")

        eventlet.spawn_after(0.1, self.send_continuous_messages)


    def send_hardware_data_to_frontend(self):
        """Send hardware monitoring data to the frontend."""
        if not self.running:
            return

        self.socketio.emit('memory_channel', {'data': self.memoryUsage})
        self.socketio.emit('cpu_channel', {
            'data': {
                'usage': self.cpuCoreUsage,
                'temp': self.cpuTemperature
            }
        })

        eventlet.spawn_after(1.0, self.send_hardware_data_to_frontend)
