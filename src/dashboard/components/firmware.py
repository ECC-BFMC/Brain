import json
import os
import time
import subprocess
import urllib.request
import urllib.error
import shutil
import glob as glob_module
from urllib.parse import urlparse, quote

from flask import jsonify


class FirmwareManager:
    """Handles Nucleo firmware check, download, and flash operations.

    The firmware source repo is configurable (default ECC-BFMC/Embedded_Platform)
    and the specific .bin to pull can be picked from any .bin found anywhere in
    that repo's tree. Unlike the Brain update, the firmware repo is *never* cloned
    -- we only read it over the GitHub HTTP API / raw URLs, so no .git is created.
    """

    FIRMWARE_REPO = 'ECC-BFMC/Embedded_Platform'
    FIRMWARE_FILE_PATH = 'cmake_build/NUCLEO_F401RE/develop/GCC_ARM/robot_car.bin'
    GITHUB_API_BASE = 'https://api.github.com'
    USER_AGENT = 'BFMC-Brain'
    NUCLEO_MOUNT_PATTERN = '/media/pi/NOD_F401RE*'

    def __init__(self, repo_path):
        self.repo_path = repo_path

    def _get_firmware_dir(self):
        return os.path.join(self.repo_path, 'runtime', 'firmware')

    # ----------------------------- source config -----------------------------

    def _config_path(self):
        return os.path.join(self.repo_path, 'runtime', 'firmware_config.json')

    def _load_config(self):
        """Read the firmware source config. Empty values fall back to the default
        Embedded_Platform repo and its robot_car.bin path."""
        cfg = {'url': '', 'branch': '', 'file_path': ''}
        path = self._config_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cfg['url'] = str(data.get('url') or '').strip()
                    cfg['branch'] = str(data.get('branch') or '').strip()
                    cfg['file_path'] = str(data.get('file_path') or '').strip()
            except (ValueError, OSError):
                pass
        return cfg

    def _save_config(self, cfg):
        path = self._config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(cfg, f, indent=2)

    def _parse_github_repo(self, url):
        """Return 'owner/repo' for a github.com URL (https/ssh/scp), else None."""
        if not url:
            return None
        u = url.strip()
        if u.startswith('git@github.com:'):
            path = u[len('git@github.com:'):]
        elif u.startswith('ssh://'):
            parsed = urlparse(u)
            if (parsed.hostname or '').lower() != 'github.com':
                return None
            path = parsed.path.lstrip('/')
        elif u.startswith('https://') or u.startswith('http://'):
            parsed = urlparse(u)
            if (parsed.hostname or '').lower() not in ('github.com', 'www.github.com'):
                return None
            path = parsed.path.lstrip('/')
        else:
            return None
        if path.endswith('.git'):
            path = path[:-4]
        parts = [p for p in path.split('/') if p]
        if len(parts) < 2:
            return None
        return f'{parts[0]}/{parts[1]}'

    def _resolve_repo(self, cfg):
        """The owner/repo to read firmware from: the configured URL if it's a
        valid GitHub repo, else the default Embedded_Platform."""
        if cfg.get('url'):
            gh = self._parse_github_repo(cfg['url'])
            if gh:
                return gh
        return self.FIRMWARE_REPO

    # ----------------------------- access token (private repos) -----------------------------

    def _token_path(self):
        # Stored alongside the Brain deploy key in the git-ignored keys dir so the
        # secret is never committed.
        return os.path.join(self.repo_path, 'runtime', 'update_keys', 'firmware_token')

    def _load_token(self):
        path = self._token_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return f.read().strip()
            except OSError:
                return ''
        return ''

    def _has_token(self):
        return bool(self._load_token())

    def _auth_headers(self):
        headers = {'User-Agent': self.USER_AGENT, 'Accept': 'application/vnd.github+json'}
        token = self._load_token()
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def _github_get(self, path):
        url = f'{self.GITHUB_API_BASE}{path}'
        req = urllib.request.Request(url, headers=self._auth_headers())
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())

    def _download_blob(self, repo, branch, file_path):
        """Fetch a file's raw bytes. With a token we use the Contents API (works
        for private repos); without one we use the public raw host."""
        token = self._load_token()
        if token:
            api = (f'{self.GITHUB_API_BASE}/repos/{repo}/contents/'
                   f"{'/'.join(quote(s) for s in file_path.split('/'))}?ref={quote(branch)}")
            req = urllib.request.Request(api, headers={
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/vnd.github.raw',
                'Authorization': f'Bearer {token}',
            })
        else:
            raw_path = '/'.join(quote(seg) for seg in file_path.split('/'))
            raw_url = f'https://raw.githubusercontent.com/{repo}/{quote(branch)}/{raw_path}'
            req = urllib.request.Request(raw_url, headers={'User-Agent': self.USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()

    def _resolve_branch(self, cfg, repo):
        """Configured branch, else the repo's default branch (never assume
        master -- forks may differ)."""
        if cfg.get('branch'):
            return cfg['branch']
        try:
            info = self._github_get(f'/repos/{repo}')
            if isinstance(info, dict) and info.get('default_branch'):
                return info['default_branch']
        except Exception:
            pass
        return 'master'

    def _resolve_file_path(self, cfg):
        return cfg.get('file_path') or self.FIRMWARE_FILE_PATH

    def _list_local_bin_files(self):
        """List .bin files available in the local firmware folder."""
        fw_dir = self._get_firmware_dir()
        if not os.path.isdir(fw_dir):
            return []

        files = []
        for entry in os.scandir(fw_dir):
            if not entry.is_file() or not entry.name.lower().endswith('.bin'):
                continue

            stat = entry.stat()
            files.append({
                'name': entry.name,
                'size': stat.st_size,
                'modified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stat.st_mtime)),
                'is_default': entry.name == 'robot_car.bin',
            })

        files.sort(key=lambda item: (0 if item['is_default'] else 1, item['name'].lower()))
        return files

    def _resolve_local_firmware_path(self, filename):
        """Resolve and validate a firmware filename inside the firmware folder."""
        if not filename:
            raise ValueError('No firmware filename was provided.')

        normalized_name = os.path.basename(str(filename).strip())
        if normalized_name != str(filename).strip():
            raise ValueError('Invalid firmware filename.')

        if not normalized_name.lower().endswith('.bin'):
            raise ValueError('Only .bin firmware files can be flashed.')

        firmware_dir = os.path.abspath(self._get_firmware_dir())
        fw_path = os.path.abspath(os.path.join(firmware_dir, normalized_name))
        if os.path.commonpath([firmware_dir, fw_path]) != firmware_dir:
            raise ValueError('Firmware file must be inside the firmware folder.')

        return fw_path, normalized_name

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

    def _latest_commit_for(self, repo, branch, file_path):
        """Return (sha, date, message) of the latest commit touching file_path on
        branch, or (None, ...) if there are none."""
        q = quote(file_path)
        commits = self._github_get(
            f'/repos/{repo}/commits?path={q}&sha={quote(branch)}&per_page=1')
        if not commits:
            return None, '', ''
        c = commits[0]
        return (c['sha'],
                c['commit']['committer']['date'],
                c['commit']['message'].split('\n')[0])

    def handle_check(self):
        """Check if a newer build of the selected .bin is available on the
        configured firmware repo/branch."""
        try:
            cfg = self._load_config()
            repo = self._resolve_repo(cfg)
            branch = self._resolve_branch(cfg, repo)
            file_path = self._resolve_file_path(cfg)
            saved_name = os.path.basename(file_path)

            remote_sha, remote_date, remote_message = self._latest_commit_for(repo, branch, file_path)
            if not remote_sha:
                return jsonify({'success': False, 'error': f'No commits found for "{file_path}" on {repo}@{branch}.'}), 404

            local_info = self._get_local_info()
            # Only treat the stored sha as ours if it was for this same file.
            same_file = bool(local_info) and local_info.get('file_path', '') == file_path
            local_sha = local_info.get('commit_sha', '') if same_file else ''

            fw_path = os.path.join(self._get_firmware_dir(), saved_name)
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
                'local_date': local_info.get('downloaded_at', '') if same_file else '',
                'source': repo,
                'branch': branch,
                'file_path': file_path,
                'file_name': saved_name,
            })
        except urllib.error.HTTPError as e:
            return self._github_http_error(e)
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to reach GitHub: {e.reason}'}), 502
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def _github_http_error(self, e):
        """Map a GitHub HTTP error to a response, flagging the private-repo case so
        the UI can offer to add an access token."""
        if e.code in (404, 401, 403):
            if not self._has_token():
                return jsonify({
                    'success': False,
                    'auth_required': True,
                    'error': ("Couldn't read this repository. If it's private, add a read-only "
                              "access token, then try again."),
                }), 404
            return jsonify({
                'success': False,
                'auth_required': True,
                'error': ('Access denied. The token may be invalid, expired, or lack read access '
                          'to this repository.'),
            }), 403
        return jsonify({'success': False, 'error': f'GitHub returned an error: {e.code}'}), 502

    def handle_download(self):
        """Download the selected .bin from the configured firmware repo/branch."""
        try:
            cfg = self._load_config()
            repo = self._resolve_repo(cfg)
            branch = self._resolve_branch(cfg, repo)
            file_path = self._resolve_file_path(cfg)
            saved_name = os.path.basename(file_path)

            remote_sha, _, _ = self._latest_commit_for(repo, branch, file_path)
            if not remote_sha:
                return jsonify({'success': False, 'error': f'No commits found for "{file_path}" on {repo}@{branch}.'}), 404

            firmware_data = self._download_blob(repo, branch, file_path)

            fw_dir = self._get_firmware_dir()
            os.makedirs(fw_dir, exist_ok=True)
            fw_path = os.path.join(fw_dir, saved_name)

            with open(fw_path, 'wb') as f:
                f.write(firmware_data)

            self._save_local_info({
                'commit_sha': remote_sha,
                'file_path': file_path,
                'file_name': saved_name,
                'source': repo,
                'branch': branch,
                'downloaded_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'file_size': len(firmware_data),
            })

            return jsonify({
                'success': True,
                'message': f'Downloaded {saved_name} ({len(firmware_data)} bytes) from {repo}@{branch}. Saved to runtime/firmware/{saved_name}.'
            })
        except urllib.error.HTTPError as e:
            return jsonify({'success': False, 'error': f'Failed to download firmware (HTTP {e.code}).'}), 502
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to download firmware: {e.reason}'}), 502
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- source / file selection -----------------------------

    def handle_get_source(self):
        """Report the configured firmware repo, branch, and selected .bin."""
        try:
            cfg = self._load_config()
            repo = self._resolve_repo(cfg)
            return jsonify({
                'success': True,
                'url': cfg.get('url') or '',
                'branch': cfg.get('branch') or '',
                'file_path': self._resolve_file_path(cfg),
                'repo': repo,
                'default_repo': self.FIRMWARE_REPO,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_set_source(self, url):
        """Persist the firmware repo URL. Empty resets to the default repo. A
        repo change clears the selected file so the student re-picks one."""
        try:
            url = (url or '').strip()
            if url and not self._parse_github_repo(url):
                return jsonify({
                    'success': False,
                    'error': 'Enter a GitHub repository URL (e.g. https://github.com/owner/repo).'
                }), 400

            cfg = self._load_config()
            if url != cfg.get('url', ''):
                cfg['file_path'] = ''   # different repo -> old path is meaningless
            cfg['url'] = url
            self._save_config(cfg)

            message = (f'Firmware source set to {self._parse_github_repo(url)}.' if url
                       else f'Firmware source reset to {self.FIRMWARE_REPO}.')
            return jsonify({'success': True, 'url': url, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_list_repo_bins(self):
        """Scan the whole configured repo tree and return every .bin path, so the
        student can pick which firmware to pull."""
        try:
            cfg = self._load_config()
            repo = self._resolve_repo(cfg)
            branch = self._resolve_branch(cfg, repo)

            tree = self._github_get(f'/repos/{repo}/git/trees/{quote(branch)}?recursive=1')
            entries = tree.get('tree', []) if isinstance(tree, dict) else []
            bins = sorted(
                e['path'] for e in entries
                if e.get('type') == 'blob' and str(e.get('path', '')).lower().endswith('.bin')
            )

            return jsonify({
                'success': True,
                'files': bins,
                'selected_file': self._resolve_file_path(cfg),
                'repo': repo,
                'branch': branch,
                'truncated': bool(tree.get('truncated')) if isinstance(tree, dict) else False,
            })
        except urllib.error.HTTPError as e:
            return self._github_http_error(e)
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to reach GitHub: {e.reason}'}), 502
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_list_branches(self):
        """List the branches of the configured firmware repo so the student can
        pick which one to pull firmware from."""
        try:
            cfg = self._load_config()
            repo = self._resolve_repo(cfg)

            default_branch = ''
            try:
                info = self._github_get(f'/repos/{repo}')
                if isinstance(info, dict):
                    default_branch = info.get('default_branch', '') or ''
            except urllib.error.HTTPError:
                raise
            except Exception:
                pass

            data = self._github_get(f'/repos/{repo}/branches?per_page=100')
            branches = sorted(b.get('name') for b in data if isinstance(b, dict) and b.get('name'))

            return jsonify({
                'success': True,
                'branches': branches,
                'default_branch': default_branch,
                'selected_branch': cfg.get('branch') or default_branch,
                'repo': repo,
            })
        except urllib.error.HTTPError as e:
            return self._github_http_error(e)
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to reach GitHub: {e.reason}'}), 502
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_set_branch(self, branch):
        """Persist which branch of the firmware repo to pull from. Empty resets to
        the repo's default branch."""
        try:
            branch = (branch or '').strip()
            if branch.startswith('-') or any(c.isspace() for c in branch):
                return jsonify({'success': False, 'error': 'Invalid branch name.'}), 400

            cfg = self._load_config()
            cfg['branch'] = branch
            self._save_config(cfg)
            message = (f'Firmware branch set to "{branch}".' if branch
                       else 'Firmware branch reset to the repository default.')
            return jsonify({'success': True, 'selected_branch': branch, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_set_file(self, file_path):
        """Persist which .bin in the source repo to pull."""
        try:
            fp = (file_path or '').strip().lstrip('/')
            if not fp.lower().endswith('.bin'):
                return jsonify({'success': False, 'error': 'Select a .bin file.'}), 400
            if '..' in fp.split('/'):
                return jsonify({'success': False, 'error': 'Invalid file path.'}), 400

            cfg = self._load_config()
            cfg['file_path'] = fp
            self._save_config(cfg)
            return jsonify({'success': True, 'file_path': fp,
                            'message': f'Firmware file set to {fp}.'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- access token -----------------------------

    def handle_get_token(self):
        """Report whether a private-repo access token is configured. The token
        itself is never returned."""
        try:
            return jsonify({'success': True, 'has_token': self._has_token()})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_set_token(self, token):
        """Store a read-only GitHub token for reaching a private firmware repo,
        verifying it can actually see the configured repo before saving."""
        try:
            tok = (token or '').strip()
            if not tok:
                return jsonify({'success': False, 'error': 'Paste an access token first.'}), 400

            # Verify against the configured repo so we don't store a dud.
            cfg = self._load_config()
            repo = self._resolve_repo(cfg)
            api = f'{self.GITHUB_API_BASE}/repos/{repo}'
            req = urllib.request.Request(api, headers={
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {tok}',
            })
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    return jsonify({
                        'success': False,
                        'error': f"That token can't read {repo}. Check it has Contents: read access to this repo.",
                    }), 400
                raise

            key_dir = os.path.dirname(self._token_path())
            os.makedirs(key_dir, exist_ok=True)
            fd = os.open(self._token_path(), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, (tok + '\n').encode())
            finally:
                os.close(fd)
            try:
                os.chmod(self._token_path(), 0o600)
            except OSError:
                pass

            return jsonify({'success': True, 'has_token': True,
                            'message': f'Access token saved and verified against {repo}.'})
        except urllib.error.URLError as e:
            return jsonify({'success': False, 'error': f'Failed to reach GitHub: {e.reason}'}), 502
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_delete_token(self):
        """Remove the stored access token."""
        try:
            path = self._token_path()
            if os.path.exists(path):
                os.remove(path)
            return jsonify({'success': True, 'has_token': False, 'message': 'Access token removed.'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_list_local_files(self):
        """Return the local .bin files available for manual flashing."""
        try:
            files = self._list_local_bin_files()
            return jsonify({
                'success': True,
                'files': files,
                'selected_file': files[0]['name'] if files else ''
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def _flash_firmware_file(self, fw_path, filename_for_target):
        """Flash the selected firmware file to the Nucleo board."""
        if not os.path.exists(fw_path):
            return jsonify({
                'success': False,
                'error': f'Firmware file "{filename_for_target}" was not found.'
            }), 400

        fw_size = os.path.getsize(fw_path)
        if fw_size == 0:
            return jsonify({
                'success': False,
                'error': f'Firmware file "{filename_for_target}" is empty.'
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

        dest_path = os.path.join(nucleo_mount, filename_for_target)
        shutil.copy2(fw_path, dest_path)

        subprocess.run(['sync'], timeout=10)

        return jsonify({
            'success': True,
            'message': f'Firmware "{filename_for_target}" flashed successfully to {nucleo_mount}. The Nucleo will reset automatically.'
        })

    def handle_flash(self):
        """Flash the most recently downloaded firmware (or robot_car.bin) to the
        Nucleo board via its USB mass storage."""
        try:
            info = self._get_local_info()
            target = (info or {}).get('file_name') or 'robot_car.bin'
            fw_path, filename = self._resolve_local_firmware_path(target)
            return self._flash_firmware_file(fw_path, filename)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except PermissionError:
            return jsonify({'success': False, 'error': 'Permission denied writing to Nucleo. Try running with sudo.'}), 403
        except OSError as e:
            return jsonify({'success': False, 'error': f'Failed to flash firmware: {e}'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_flash_selected(self, filename):
        """Flash a selected local .bin file to the Nucleo board."""
        try:
            fw_path, normalized_name = self._resolve_local_firmware_path(filename)
            return self._flash_firmware_file(fw_path, normalized_name)
        except PermissionError:
            return jsonify({'success': False, 'error': 'Permission denied writing to Nucleo. Try running with sudo.'}), 403
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except OSError as e:
            return jsonify({'success': False, 'error': f'Failed to flash firmware: {e}'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
