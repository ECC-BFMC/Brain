import logging
import os
import re
import shlex
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager

from flask import jsonify


LOGGER = logging.getLogger(__name__)


class WifiCommandError(RuntimeError):
    """Raised when NetworkManager rejects a dashboard operation."""


class WifiPermissionError(WifiCommandError):
    """Raised when Polkit denies a required NetworkManager action."""


class WifiManager:
    """Manage persistent Wi-Fi profiles through NetworkManager."""

    PROTECTED_CONNECTIONS = {'rpi-hotspot', 'preconfigured'}
    WIFI_TYPES = {'802-11-wireless', 'wifi'}
    TERMINAL_STATES = {'connected', 'completed', 'failed'}
    MAX_OPERATIONS = 50
    PERMISSION_ENABLE_WIFI = 'org.freedesktop.NetworkManager.enable-disable-wifi'
    PERMISSION_NETWORK_CONTROL = 'org.freedesktop.NetworkManager.network-control'
    PERMISSION_MODIFY_SYSTEM = 'org.freedesktop.NetworkManager.settings.modify.system'
    PERMISSION_WIFI_SCAN = 'org.freedesktop.NetworkManager.wifi.scan'

    def __init__(self, repo_path):
        self.repo_path = repo_path
        config = self._load_fallback_config()
        self.interface = os.environ.get('WIFI_IFACE', config.get('IFACE', 'wlan0'))
        self.hotspot_name = os.environ.get(
            'WIFI_HOTSPOT_CONNECTION',
            config.get('CON_NAME', 'rpi-hotspot'),
        )
        self.hotspot_ssid = os.environ.get(
            'WIFI_HOTSPOT_SSID',
            config.get('SSID', 'BFMCDemoCar'),
        )
        self.delete_hotspot_on_client = (
            config.get('DELETE_AP_ON_CLIENT', 'true').lower() == 'true'
        )
        self.lock_file = os.environ.get(
            'WIFI_LOCK_FILE',
            '/run/rpi-wifi-fallback/operation.lock',
        )
        self.hotspot_request_file = os.environ.get(
            'WIFI_HOTSPOT_REQUEST_FILE',
            os.path.join(
                os.path.dirname(self.lock_file),
                'immediate-hotspot',
            ),
        )
        self.config_file = config.get(
            '_path',
            '/opt/rpi-wifi-fallback/config.env',
        )

        self._state_lock = threading.Lock()
        self._operations = {}
        self._active_operation_id = None

    def _load_fallback_config(self):
        candidates = [
            os.environ.get('WIFI_FALLBACK_CONFIG'),
            '/opt/rpi-wifi-fallback/config.env',
            os.path.join(
                self.repo_path,
                'services',
                'rpi-wifi-fallback',
                'config.env',
            ),
        ]
        for path in candidates:
            if not path or not os.path.isfile(path):
                continue

            config = {'_path': path}
            try:
                with open(path, 'r', encoding='utf-8') as config_file:
                    for raw_line in config_file:
                        line = raw_line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        key, raw_value = line.split('=', 1)
                        if key not in {
                            'SSID',
                            'IFACE',
                            'CON_NAME',
                            'DELETE_AP_ON_CLIENT',
                        }:
                            continue
                        values = shlex.split(raw_value, comments=True)
                        config[key] = values[0] if values else ''
                return config
            except (OSError, ValueError):
                LOGGER.exception('Cannot read Wi-Fi fallback config %s', path)

        return {}

    @staticmethod
    def _split_terse_line(line):
        """Split nmcli terse output while honoring its backslash escaping."""
        fields = []
        current = []
        escaped = False
        for character in line:
            if escaped:
                current.append(character)
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == ':':
                fields.append(''.join(current))
                current = []
            else:
                current.append(character)
        if escaped:
            current.append('\\')
        fields.append(''.join(current))
        return fields

    @staticmethod
    def _command_error(result, fallback):
        return (result.stderr or result.stdout or fallback).strip()

    def _nmcli(
        self,
        *args,
        timeout=15,
        check=True,
        allowed_returncodes=(0,),
    ):
        try:
            result = subprocess.run(
                ['nmcli', *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as error:
            raise WifiCommandError('nmcli is not installed') from error
        except subprocess.TimeoutExpired as error:
            raise WifiCommandError('NetworkManager command timed out') from error
        except OSError as error:
            raise WifiCommandError(str(error)) from error

        if check and result.returncode not in allowed_returncodes:
            message = self._command_error(
                result,
                'NetworkManager operation failed',
            )
            normalized_message = message.lower()
            if (
                'insufficient privileges' in normalized_message
                or 'not authorized' in normalized_message
                or 'not authorised' in normalized_message
            ):
                raise WifiPermissionError(message)
            raise WifiCommandError(message)
        return result

    def _require_permissions(self, *required_permissions):
        result = self._nmcli(
            '--terse',
            '--escape',
            'no',
            '--fields',
            'PERMISSION,VALUE',
            'general',
            'permissions',
        )
        permissions = {}
        for line in result.stdout.splitlines():
            permission, separator, value = line.rpartition(':')
            if separator:
                permissions[permission] = value.strip().lower()

        denied = [
            permission
            for permission in required_permissions
            if permissions.get(permission) != 'yes'
        ]
        if denied:
            denied_names = ', '.join(denied)
            raise WifiPermissionError(
                'Dashboard service is not authorized by Polkit for: '
                f'{denied_names}. From the Brain repository root run '
                '"bash services/rpi-wifi-fallback/install.sh" in an '
                'interactive SSH or local terminal.'
            )

    @staticmethod
    def _error_status(error):
        return 403 if isinstance(error, WifiPermissionError) else 500

    def _connection_property(self, connection_uuid, property_name):
        result = self._nmcli(
            '--terse',
            '--escape',
            'no',
            '--get-values',
            property_name,
            'connection',
            'show',
            'uuid',
            connection_uuid,
            check=False,
        )
        return result.stdout.rstrip('\r\n') if result.returncode == 0 else ''

    def _wifi_profiles(self):
        result = self._nmcli(
            '--terse',
            '--fields',
            'UUID,NAME,TYPE',
            'connection',
            'show',
        )
        active_result = self._nmcli(
            '--terse',
            '--escape',
            'no',
            '--fields',
            'UUID',
            'connection',
            'show',
            '--active',
        )
        active_uuids = {
            line.strip()
            for line in active_result.stdout.splitlines()
            if line.strip()
        }

        profiles = []
        for line in result.stdout.splitlines():
            fields = self._split_terse_line(line)
            if len(fields) != 3:
                continue
            connection_uuid, name, connection_type = fields
            if connection_type not in self.WIFI_TYPES:
                continue

            mode = self._connection_property(
                connection_uuid,
                '802-11-wireless.mode',
            )
            ssid = self._connection_property(
                connection_uuid,
                '802-11-wireless.ssid',
            )
            profiles.append({
                'uuid': connection_uuid,
                'name': name,
                'ssid': ssid or name,
                'mode': mode or 'infrastructure',
                'active': connection_uuid in active_uuids,
            })
        return profiles

    def handle_list(self):
        """Return saved client Wi-Fi profiles."""
        try:
            networks = [
                {
                    'uuid': profile['uuid'],
                    'name': profile['ssid'],
                    'active': profile['active'],
                }
                for profile in self._wifi_profiles()
                if (
                    profile['mode'] != 'ap'
                    and profile['name'] not in self.PROTECTED_CONNECTIONS
                    and profile['name'] != self.hotspot_name
                )
            ]
            networks.sort(key=lambda network: (not network['active'], network['name'].lower()))
            return jsonify({'success': True, 'networks': networks})
        except WifiCommandError as error:
            LOGGER.error('Cannot list Wi-Fi profiles: %s', error)
            return jsonify({'success': False, 'error': str(error)}), 500

    def handle_scan(self):
        """Force a scan and return visible access points grouped by network."""
        try:
            self._require_permissions(self.PERMISSION_WIFI_SCAN)
            profiles = [
                profile
                for profile in self._wifi_profiles()
                if (
                    profile['mode'] != 'ap'
                    and profile['name'] not in self.PROTECTED_CONNECTIONS
                    and profile['name'] != self.hotspot_name
                )
            ]
            saved_ssids = {profile['ssid'] for profile in profiles}
            active_ssids = {
                profile['ssid']
                for profile in profiles
                if profile['active']
            }
            result = self._nmcli(
                '--terse',
                '--escape',
                'yes',
                '--fields',
                'IN-USE,SSID,SIGNAL,SECURITY',
                'device',
                'wifi',
                'list',
                'ifname',
                self.interface,
                '--rescan',
                'yes',
                timeout=20,
            )

            strongest = {}
            for line in result.stdout.splitlines():
                fields = self._split_terse_line(line)
                if len(fields) != 4:
                    continue

                in_use, ssid, signal_value, security_value = fields
                ssid = ssid.strip()
                if not ssid or ssid == self.hotspot_ssid:
                    continue
                try:
                    signal = max(0, min(100, int(signal_value)))
                except ValueError:
                    continue

                raw_security = security_value.strip()
                secured = raw_security not in {'', '--'}
                security = raw_security if secured else 'Open'
                key = (ssid, security)
                network = {
                    'ssid': ssid,
                    'signal': signal,
                    'security': security,
                    'secured': secured,
                    'saved': ssid in saved_ssids,
                    'active': in_use.strip() == '*' or ssid in active_ssids,
                }
                previous = strongest.get(key)
                if previous is None or signal > previous['signal']:
                    strongest[key] = network

            networks = list(strongest.values())
            networks.sort(
                key=lambda network: (
                    not network['active'],
                    not network['saved'],
                    -network['signal'],
                    network['ssid'].lower(),
                )
            )
            return jsonify({'success': True, 'networks': networks})
        except WifiCommandError as error:
            LOGGER.error('Cannot scan Wi-Fi networks: %s', error)
            return jsonify({
                'success': False,
                'error': str(error),
            }), self._error_status(error)

    def _prune_operations_locked(self):
        if len(self._operations) <= self.MAX_OPERATIONS:
            return
        completed = sorted(
            (
                operation
                for operation in self._operations.values()
                if operation['state'] in self.TERMINAL_STATES
            ),
            key=lambda operation: operation['updated_at'],
        )
        for operation in completed[:len(self._operations) - self.MAX_OPERATIONS]:
            self._operations.pop(operation['id'], None)

    def _begin_operation(self, action, network_name):
        with self._state_lock:
            if self._active_operation_id is not None:
                return None

            operation_id = uuid.uuid4().hex
            now = time.time()
            operation = {
                'id': operation_id,
                'action': action,
                'network': network_name,
                'state': 'preparing',
                'message': f'Preparing to {action} "{network_name}"',
                'created_at': now,
                'updated_at': now,
            }
            self._operations[operation_id] = operation
            self._active_operation_id = operation_id
            self._prune_operations_locked()
            return operation_id

    def _update_operation(self, operation_id, state, message):
        with self._state_lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return
            operation['state'] = state
            operation['message'] = message
            operation['updated_at'] = time.time()
            if state in self.TERMINAL_STATES:
                if self._active_operation_id == operation_id:
                    self._active_operation_id = None

    def handle_operation(self, operation_id):
        with self._state_lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return jsonify({
                    'success': False,
                    'error': 'Wi-Fi operation not found',
                }), 404
            response = dict(operation)
        return jsonify({'success': True, 'operation': response})

    @contextmanager
    def _radio_lock(self):
        """Serialize dashboard radio changes with the root fallback service."""
        if os.name != 'posix':
            yield
            return

        import fcntl

        try:
            lock_handle = open(self.lock_file, 'a+', encoding='utf-8')
        except OSError as error:
            raise WifiCommandError(
                f'Cannot open Wi-Fi operation lock {self.lock_file}: {error}'
            ) from error

        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()

    def _hotspot_profile(self):
        for profile in self._wifi_profiles():
            if profile['mode'] == 'ap' or profile['name'] == self.hotspot_name:
                return profile
        return None

    def _stop_hotspot(self):
        hotspot = self._hotspot_profile()
        if hotspot is None:
            return

        self._nmcli(
            'connection',
            'modify',
            'uuid',
            hotspot['uuid'],
            'connection.autoconnect',
            'no',
        )
        if hotspot['active']:
            self._nmcli(
                '--wait',
                '10',
                'connection',
                'down',
                'uuid',
                hotspot['uuid'],
                timeout=15,
            )

    def _delete_profile(self, connection_uuid, ignore_missing=False):
        result = self._nmcli(
            'connection',
            'delete',
            'uuid',
            connection_uuid,
            check=False,
        )
        if result.returncode == 0:
            return
        if ignore_missing and result.returncode == 10:
            return
        raise WifiCommandError(
            self._command_error(result, 'Cannot delete Wi-Fi profile')
        )

    def _start_fallback(self):
        """Start hotspot restoration after releasing the shared radio lock."""
        candidates = [
            '/opt/rpi-wifi-fallback/fallback.sh',
            os.path.join(
                self.repo_path,
                'services',
                'rpi-wifi-fallback',
                'fallback.sh',
            ),
        ]
        fallback_script = next(
            (path for path in candidates if os.path.isfile(path)),
            None,
        )
        if fallback_script is None:
            LOGGER.error('Cannot restore hotspot: fallback.sh was not found')
            return False

        env = os.environ.copy()
        env['CONFIG_FILE'] = self.config_file
        env['LOG'] = '/tmp/rpi-wifi-fallback.log'
        env['LOCK_FILE'] = self.lock_file
        env['HOTSPOT_REQUEST_FILE'] = self.hotspot_request_file
        # The systemd/dispatcher path waits for an in-flight dashboard
        # operation. This direct backup launch happens after the dashboard lock
        # is released, so it must not queue behind another reconciler.
        env['LOCK_WAIT_SECONDS'] = '0'
        try:
            subprocess.Popen(
                ['/bin/bash', fallback_script, 'up'],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except OSError:
            LOGGER.exception('Cannot launch Wi-Fi fallback')
            return False

    def _request_immediate_hotspot(self):
        """Tell a dispatcher-started reconciler to skip its reconnect grace."""
        try:
            with open(self.hotspot_request_file, 'w', encoding='utf-8'):
                pass
            return True
        except OSError:
            LOGGER.exception(
                'Cannot create immediate hotspot request %s',
                self.hotspot_request_file,
            )
            return False

    def _cancel_immediate_hotspot(self):
        """Remove a request when the client connection was restored."""
        try:
            os.remove(self.hotspot_request_file)
        except FileNotFoundError:
            pass
        except OSError:
            LOGGER.exception(
                'Cannot remove immediate hotspot request %s',
                self.hotspot_request_file,
            )

    @staticmethod
    def _valid_wpa_psk(password):
        if 8 <= len(password) <= 63:
            return True
        return len(password) == 64 and re.fullmatch(r'[0-9a-fA-F]{64}', password)

    def _create_candidate(
        self,
        ssid,
        password,
        candidate_name,
        open_network=False,
    ):
        self._nmcli(
            'connection',
            'add',
            'type',
            'wifi',
            'ifname',
            self.interface,
            'con-name',
            candidate_name,
            'autoconnect',
            'no',
            'ssid',
            ssid,
        )

        candidate_uuid = self._connection_property_by_name(
            candidate_name,
            'connection.uuid',
        )
        if not candidate_uuid:
            self._nmcli(
                'connection',
                'delete',
                'id',
                candidate_name,
                check=False,
            )
            raise WifiCommandError('NetworkManager did not return the new profile UUID')

        try:
            modify_args = [
                'connection',
                'modify',
                'uuid',
                candidate_uuid,
                '802-11-wireless.mode',
                'infrastructure',
                '802-11-wireless.cloned-mac-address',
                'permanent',
                'connection.permissions',
                '',
                'connection.autoconnect',
                'no',
                'connection.autoconnect-priority',
                '20',
            ]
            if not open_network:
                modify_args.extend([
                    '802-11-wireless-security.key-mgmt',
                    'wpa-psk',
                    '802-11-wireless-security.psk',
                    password,
                    '802-11-wireless-security.psk-flags',
                    '0',
                ])
            self._nmcli(*modify_args)
        except WifiCommandError:
            self._delete_profile(candidate_uuid, ignore_missing=True)
            raise
        return candidate_uuid

    def _connection_property_by_name(self, name, property_name):
        result = self._nmcli(
            '--terse',
            '--escape',
            'no',
            '--get-values',
            property_name,
            'connection',
            'show',
            'id',
            name,
            check=False,
        )
        if result.returncode != 0:
            return ''
        return result.stdout.splitlines()[0].strip() if result.stdout else ''

    def handle_add(self, data):
        """Create a profile, then switch the radio after returning HTTP 202."""
        if not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': 'A JSON request body is required',
            }), 400

        ssid_value = data.get('ssid', '')
        password = data.get('password', '')
        security = data.get('security', 'secured')
        ssid = ssid_value.strip() if isinstance(ssid_value, str) else ''
        open_network = security == 'open'

        if security not in {'open', 'secured'}:
            return jsonify({
                'success': False,
                'error': 'Wi-Fi security type is invalid',
            }), 400
        if (
            not ssid
            or not isinstance(password, str)
            or (not open_network and not password)
        ):
            return jsonify({
                'success': False,
                'error': (
                    'SSID is required'
                    if open_network
                    else 'SSID and password are required'
                ),
            }), 400
        if not open_network and not self._valid_wpa_psk(password):
            return jsonify({
                'success': False,
                'error': 'WPA password must contain 8-63 characters, or 64 hexadecimal characters',
            }), 400

        try:
            self._require_permissions(
                self.PERMISSION_ENABLE_WIFI,
                self.PERMISSION_NETWORK_CONTROL,
                self.PERMISSION_MODIFY_SYSTEM,
                self.PERMISSION_WIFI_SCAN,
            )
        except WifiCommandError as error:
            return jsonify({
                'success': False,
                'error': str(error),
            }), self._error_status(error)

        operation_id = self._begin_operation('add', ssid)
        if operation_id is None:
            return jsonify({
                'success': False,
                'error': 'Another Wi-Fi operation is already running',
            }), 409

        candidate_name = f'brain-candidate-{operation_id[:8]}'
        try:
            with self._radio_lock():
                profiles = self._wifi_profiles()
                existing_profiles = [
                    profile
                    for profile in profiles
                    if profile['mode'] != 'ap' and profile['ssid'] == ssid
                ]
                active_client = next(
                    (
                        profile
                        for profile in profiles
                        if profile['mode'] != 'ap' and profile['active']
                    ),
                    None,
                )
                if open_network:
                    candidate_uuid = self._create_candidate(
                        ssid,
                        password,
                        candidate_name,
                        open_network=True,
                    )
                else:
                    candidate_uuid = self._create_candidate(
                        ssid,
                        password,
                        candidate_name,
                    )
        except WifiCommandError as error:
            LOGGER.error('Cannot prepare Wi-Fi profile %r: %s', ssid, error)
            self._update_operation(
                operation_id,
                'failed',
                f'Could not save "{ssid}": {error}',
            )
            return jsonify({
                'success': False,
                'error': str(error),
            }), self._error_status(error)

        worker = threading.Thread(
            target=self._activate_candidate,
            args=(
                operation_id,
                ssid,
                candidate_uuid,
                [profile['uuid'] for profile in existing_profiles],
                active_client['uuid'] if active_client else None,
            ),
            daemon=True,
        )
        worker.start()

        return jsonify({
            'success': True,
            'operation_id': operation_id,
            'state': 'prepared',
            'message': (
                f'Wi-Fi profile "{ssid}" was saved. '
                'The car will now attempt to connect.'
            ),
        }), 202

    def _activate_candidate(
        self,
        operation_id,
        ssid,
        candidate_uuid,
        replaced_uuids,
        previous_active_uuid,
    ):
        time.sleep(2)
        needs_fallback = False
        failure_message = f'Could not connect to "{ssid}"'

        try:
            with self._radio_lock():
                self._update_operation(
                    operation_id,
                    'connecting',
                    f'Connecting to "{ssid}"',
                )
                self._nmcli('radio', 'wifi', 'on')
                self._nmcli(
                    'device',
                    'set',
                    self.interface,
                    'managed',
                    'yes',
                )
                self._stop_hotspot()

                connected = False
                last_error = ''
                for _ in range(3):
                    self._nmcli(
                        'device',
                        'wifi',
                        'rescan',
                        'ifname',
                        self.interface,
                        check=False,
                    )
                    result = self._nmcli(
                        '--wait',
                        '25',
                        'connection',
                        'up',
                        'uuid',
                        candidate_uuid,
                        'ifname',
                        self.interface,
                        timeout=30,
                        check=False,
                    )
                    if result.returncode == 0:
                        connected = True
                        break
                    last_error = self._command_error(
                        result,
                        'connection activation failed',
                    )

                if connected:
                    self._nmcli(
                        'connection',
                        'modify',
                        'uuid',
                        candidate_uuid,
                        'connection.id',
                        ssid,
                        'connection.autoconnect',
                        'yes',
                    )
                    for old_uuid in replaced_uuids:
                        if old_uuid != candidate_uuid:
                            self._delete_profile(old_uuid, ignore_missing=True)

                    hotspot = self._hotspot_profile()
                    if hotspot and self.delete_hotspot_on_client:
                        self._delete_profile(
                            hotspot['uuid'],
                            ignore_missing=True,
                        )

                    self._update_operation(
                        operation_id,
                        'connected',
                        f'Connected to "{ssid}"',
                    )
                    return

                self._delete_profile(candidate_uuid, ignore_missing=True)
                if last_error:
                    failure_message = f'{failure_message}: {last_error}'

                restored_previous = False
                if previous_active_uuid:
                    restore = self._nmcli(
                        '--wait',
                        '25',
                        'connection',
                        'up',
                        'uuid',
                        previous_active_uuid,
                        'ifname',
                        self.interface,
                        timeout=30,
                        check=False,
                    )
                    restored_previous = restore.returncode == 0

                if restored_previous:
                    failure_message += '; the previous Wi-Fi connection was restored'
                else:
                    needs_fallback = True
                    failure_message += '; restoring the fallback hotspot'
        except Exception as error:
            LOGGER.exception('Wi-Fi activation failed for %r', ssid)
            failure_message = f'Could not connect to "{ssid}": {error}'
            try:
                self._delete_profile(candidate_uuid, ignore_missing=True)
            except WifiCommandError:
                LOGGER.exception('Cannot clean up candidate profile %s', candidate_uuid)
            needs_fallback = True

        if needs_fallback and not self._start_fallback():
            failure_message += '; fallback could not be started'
        self._update_operation(operation_id, 'failed', failure_message)

    def _resolve_profile(self, identifier):
        profiles = self._wifi_profiles()
        exact_uuid = next(
            (profile for profile in profiles if profile['uuid'] == identifier),
            None,
        )
        if exact_uuid:
            return exact_uuid

        by_name = [
            profile
            for profile in profiles
            if profile['name'] == identifier or profile['ssid'] == identifier
        ]
        if len(by_name) == 1:
            return by_name[0]
        if len(by_name) > 1:
            raise WifiCommandError('Network name is ambiguous; refresh the list and retry')
        return None

    def handle_remove(self, identifier):
        """Remove an inactive profile now, or switch an active one to hotspot."""
        if not identifier:
            return jsonify({
                'success': False,
                'error': 'Network identifier is required',
            }), 400

        try:
            profile = self._resolve_profile(identifier)
        except WifiCommandError as error:
            return jsonify({'success': False, 'error': str(error)}), 409

        if profile is None:
            return jsonify({
                'success': False,
                'error': 'Wi-Fi profile not found',
            }), 404
        if (
            profile['mode'] == 'ap'
            or profile['name'] in self.PROTECTED_CONNECTIONS
            or profile['name'] == self.hotspot_name
        ):
            return jsonify({
                'success': False,
                'error': 'Cannot remove this connection',
            }), 400

        required_permissions = [self.PERMISSION_MODIFY_SYSTEM]
        if profile['active']:
            required_permissions.append(self.PERMISSION_NETWORK_CONTROL)
        try:
            self._require_permissions(*required_permissions)
        except WifiCommandError as error:
            return jsonify({
                'success': False,
                'error': str(error),
            }), self._error_status(error)

        operation_id = self._begin_operation('remove', profile['ssid'])
        if operation_id is None:
            return jsonify({
                'success': False,
                'error': 'Another Wi-Fi operation is already running',
            }), 409

        if not profile['active']:
            try:
                with self._radio_lock():
                    self._delete_profile(profile['uuid'])
            except WifiCommandError as error:
                self._update_operation(
                    operation_id,
                    'failed',
                    f'Could not remove "{profile["ssid"]}": {error}',
                )
                return jsonify({
                    'success': False,
                    'error': str(error),
                }), self._error_status(error)

            message = f'Network "{profile["ssid"]}" was removed'
            self._update_operation(operation_id, 'completed', message)
            return jsonify({
                'success': True,
                'operation_id': operation_id,
                'state': 'completed',
                'message': message,
            })

        worker = threading.Thread(
            target=self._remove_active_connection,
            args=(operation_id, profile),
            daemon=True,
        )
        worker.start()
        return jsonify({
            'success': True,
            'operation_id': operation_id,
            'state': 'prepared',
            'message': (
                f'Network "{profile["ssid"]}" will be removed. '
                'The fallback hotspot will start shortly.'
            ),
        }), 202

    def _remove_active_connection(self, operation_id, profile):
        time.sleep(2)
        removed = False
        restored = False
        message = f'Could not remove "{profile["ssid"]}"'

        try:
            with self._radio_lock():
                self._request_immediate_hotspot()
                self._update_operation(
                    operation_id,
                    'disconnecting',
                    f'Disconnecting from "{profile["ssid"]}"',
                )
                self._nmcli(
                    '--wait',
                    '10',
                    'connection',
                    'down',
                    'uuid',
                    profile['uuid'],
                    timeout=15,
                )
                self._delete_profile(profile['uuid'])
                removed = True
        except WifiCommandError as error:
            LOGGER.error('Cannot remove active Wi-Fi profile %s: %s', profile['uuid'], error)
            message = f'{message}: {error}'
            try:
                self._nmcli(
                    '--wait',
                    '25',
                    'connection',
                    'up',
                    'uuid',
                    profile['uuid'],
                    'ifname',
                    self.interface,
                    timeout=30,
                )
                restored = True
                self._cancel_immediate_hotspot()
                message += '; the connection was restored'
            except WifiCommandError:
                message += '; the connection could not be restored'

        if removed:
            fallback_started = self._start_fallback()
            message = f'Network "{profile["ssid"]}" was removed'
            if fallback_started:
                message += '; restoring the fallback hotspot'
            else:
                message += '; fallback could not be started'
            self._update_operation(operation_id, 'completed', message)
        else:
            if not restored:
                if self._start_fallback():
                    message += '; restoring the fallback hotspot'
                else:
                    message += '; fallback could not be started'
            self._update_operation(operation_id, 'failed', message)
