import base64
from contextlib import contextmanager
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import urllib.error
from urllib.parse import urlparse

import yaml
from flask import jsonify

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows development fallback
    fcntl = None


logger = logging.getLogger(__name__)


class UpdateManager:
    """Handles Brain codebase updates from a configurable git remote.

    The update source (repo URL + branch) lives in the ``brain`` section of
    ``runtime/config.yaml`` and is editable from the dashboard. Private repos are
    reached with a read-only access token, stored on the car only. The GitHub API
    is used for the read-only check / branch listing layer, with a git fallback
    for private, non-GitHub, rate-limited or offline repositories. Applying an
    update is always git (fetch + fast-forward, or an explicit force reset).
    """

    DEFAULT_REMOTE_NAME = 'bfmc-upstream'
    GITHUB_API_BASE = 'https://api.github.com'
    USER_AGENT = 'BFMC-Brain'

    def __init__(self, repo_path):
        self.repo_path = repo_path
        self._update_lock = threading.Lock()

    # ----------------------------- config -----------------------------

    CONFIG_SECTION = 'brain'

    def _yaml_path(self):
        return os.path.join(self.repo_path, 'runtime', 'config.yaml')

    def _read_yaml(self):
        path = self._yaml_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
            except (yaml.YAMLError, OSError):
                pass
        return {}

    def _legacy_json_config(self):
        """Read the pre-YAML runtime/update_config.json, if it still exists, so an
        already-configured car keeps working after upgrading to config.yaml."""
        path = os.path.join(self.repo_path, 'runtime', 'update_config.json')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (ValueError, OSError):
                pass
        return {}

    def _load_config(self):
        """Read the Pi-side update config from the ``brain`` section of
        runtime/config.yaml. Defaults keep zero-config behaviour: an empty url
        means "update from origin" (the repo the student cloned)."""
        cfg = {'remote_name': self.DEFAULT_REMOTE_NAME, 'url': '', 'branch': ''}
        section = self._read_yaml().get(self.CONFIG_SECTION)
        if not isinstance(section, dict):
            section = self._legacy_json_config()
        cfg['remote_name'] = str(section.get('remote_name') or cfg['remote_name']).strip()
        cfg['url'] = str(section.get('url') or '').strip()
        cfg['branch'] = str(section.get('branch') or '').strip()
        return cfg

    def _save_config(self, cfg):
        path = self._yaml_path()
        data = self._read_yaml()
        data[self.CONFIG_SECTION] = {
            'remote_name': cfg.get('remote_name', self.DEFAULT_REMOTE_NAME),
            'url': cfg.get('url', ''),
            'branch': cfg.get('branch', ''),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    # ----------------------------- access token -----------------------------

    def _key_dir(self):
        # git-ignored, untracked -> survives `git reset --hard` during updates.
        return os.path.join(self.repo_path, 'runtime', 'update_keys')

    def _token_path(self):
        return os.path.join(self._key_dir(), 'brain_token')

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

    def _auth_header_args(self):
        """git -c args injecting an HTTPS Basic auth header from the stored token
        (the token is the password; GitHub ignores the username). Empty when no
        token, so public repos clone anonymously."""
        token = self._load_token()
        if not token:
            return []
        basic = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
        return ['-c', f'http.extraHeader=Authorization: Basic {basic}']

    # ----------------------------- git helpers -----------------------------

    def _git(self, *args, timeout=30):
        # Force git to fail fast instead of blocking on an interactive prompt, and
        # inject the token (when set) so private https repos authenticate. Public
        # repos work with no token at all.
        env = dict(os.environ)
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = env.get('GIT_ASKPASS', '') or 'echo'
        return subprocess.run(
            ['git', *self._auth_header_args(), *args],
            cwd=self.repo_path,
            capture_output=True, text=True, timeout=timeout, env=env
        )

    @staticmethod
    def _to_https_url(url):
        """Convert an scp/ssh git URL to https so the token can authenticate it
        (tokens only work over https). Other URLs are returned unchanged."""
        u = (url or '').strip()
        if u.startswith('git@') and ':' in u:
            host, path = u[len('git@'):].split(':', 1)
            return f'https://{host}/{path}'
        if u.startswith('ssh://'):
            parsed = urlparse(u)
            host = parsed.hostname or ''
            path = parsed.path.lstrip('/')
            if host and path:
                return f'https://{host}/{path}'
        return u

    def _effective_url(self, url):
        """The URL git should use. With a token we force https so the token's
        Basic-auth header is actually applied; without one, leave it as entered."""
        if url and self._has_token():
            return self._to_https_url(url)
        return url

    # Markers git prints when a fetch/clone fails because of missing or rejected
    # credentials (vs. a network/other error). Used to tell the student that the
    # repo is private and how to grant the Pi access.
    _AUTH_ERROR_MARKERS = (
        'authentication failed',
        'could not read username',
        'could not read password',
        'terminal prompts disabled',
        'permission denied (publickey)',
        'permission denied (publickey,password)',
        'host key verification failed',
        'invalid username or password',
        'repository not found',          # GitHub's response for private repos you can't see
        'remote: not found',
        'access denied',
        'fatal: authentication',
        '403 forbidden',
        'support for password authentication was removed',
    )

    AUTH_REQUIRED_MESSAGE = (
        "Couldn't access this repository. If it's private, add a read-only access "
        "token, then try again."
    )

    DIVERGED_MESSAGE = (
        "The update source has a different history than this car's copy (common "
        "when switching to a fork). Use \"Discard local changes & update\" to "
        "switch to it -- this overwrites local changes to tracked files."
    )

    PERMISSION_ERROR_MESSAGE = (
        "Git cannot write to this checkout or one of its submodules. This usually "
        "means part of the repository was cloned or updated with sudo/root. On the "
        "Raspberry Pi, run: sudo chown -R $(id -u):$(id -g) ~/Documents/Brain"
    )

    UPDATE_BUSY_MESSAGE = (
        "Another repository operation is already running. Wait for it to finish, "
        "then try again."
    )

    CORRUPT_REPO_MESSAGE = (
        "The local Git checkout is damaged or incomplete. Do not continue updating "
        "this folder; restore it from a clean clone first."
    )

    @classmethod
    def _is_permission_error(cls, text):
        if not text:
            return False
        low = text.lower()
        return 'permission denied' in low and (
            'fetch_head' in low
            or 'cannot open' in low
            or 'unable to create' in low
            or 'could not lock config file' in low
        )

    @classmethod
    def _is_auth_error(cls, text):
        if not text:
            return False
        low = text.lower()
        return any(marker in low for marker in cls._AUTH_ERROR_MARKERS)

    def _is_git_repo(self):
        result = self._git('rev-parse', '--is-inside-work-tree', timeout=10)
        return result.returncode == 0 and result.stdout.strip() == 'true'

    def _origin_url(self):
        result = self._git('remote', 'get-url', 'origin', timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ''

    def _validate_repo_url(self, url):
        """Footgun guard for a trusted, Pi-local config value -- not a security
        boundary, since whoever edits the file already has shell access. Allow
        https/ssh/scp-style git URLs (SSH is required for deploy keys); block
        transports that would execute commands or read arbitrary local files."""
        if not url:
            return False, 'No repository URL is configured.'
        u = url.strip()
        lowered = u.lower()
        if u.startswith('-'):
            return False, 'Invalid repository URL.'
        if lowered.startswith('ext::') or lowered.startswith('file:'):
            return False, 'This repository URL transport is not allowed.'
        if '://' not in u:
            # scp-like form, e.g. git@github.com:owner/repo.git
            if u.startswith('git@') or ('@' in u and ':' in u):
                return True, ''
            return False, 'Unsupported repository URL format.'
        scheme = urlparse(u).scheme.lower()
        if scheme not in ('https', 'ssh'):
            return False, 'Only https:// and ssh:// repository URLs are supported.'
        return True, ''

    def _ensure_configured_remote(self, cfg):
        """Ensure the configured remote exists and points at cfg.url. An empty
        url falls back to ``origin``. Returns (remote_name, error_or_None)."""
        url = cfg.get('url', '')
        if not url:
            return 'origin', None

        ok, err = self._validate_repo_url(url)
        if not ok:
            return None, err

        # Use the SSH form when a deploy key is configured so the key is actually
        # used for auth (keys don't work over https).
        url = self._effective_url(url)

        remote = cfg['remote_name']
        existing = self._git('remote', 'get-url', remote, timeout=10)
        if existing.returncode != 0:
            add = self._git('remote', 'add', remote, url, timeout=10)
            if add.returncode != 0:
                return None, 'Failed to configure the update remote.'
        elif existing.stdout.strip() != url:
            self._git('remote', 'set-url', remote, url, timeout=10)
        return remote, None

    def _remote_default_branch(self, remote):
        """The remote's own default branch (its HEAD symref) -- independent of
        what the student has chosen to track. Empty if it can't be determined."""
        symref = self._git('ls-remote', '--symref', remote, 'HEAD', timeout=20)
        if symref.returncode == 0:
            for line in symref.stdout.splitlines():
                if line.startswith('ref:'):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].startswith('refs/heads/'):
                        return parts[1][len('refs/heads/'):]
        return ''

    def _resolve_branch(self, cfg, remote):
        """The branch to actually pull: the configured one, else the remote's
        default (never hardcode master, since forks may use main or anything)."""
        if cfg.get('branch'):
            return cfg['branch']
        default = self._remote_default_branch(remote)
        if default:
            return default
        current = self._git('rev-parse', '--abbrev-ref', 'HEAD', timeout=10).stdout.strip()
        return current if current and current != 'HEAD' else 'master'

    def _source_label(self, cfg):
        return cfg.get('url') or self._origin_url() or cfg.get('remote_name', 'origin')

    def _changed_files(self, ref_a, ref_b):
        if not ref_a or not ref_b:
            return []
        diff = self._git('diff', '--name-only', f'{ref_a}..{ref_b}', timeout=15)
        if diff.returncode != 0:
            return []
        return [line.strip() for line in diff.stdout.splitlines() if line.strip()]

    @staticmethod
    def _deps_changed(files):
        """True if a dependency manifest changed in the update range (#7)."""
        for f in files:
            if (
                os.path.basename(f) == 'requirements.txt'
                or f.endswith('frontend/package.json')
                or f.endswith('frontend/package-lock.json')
            ):
                return True
        return False

    def _cleanup_git_dir(self):
        git_dir = os.path.join(self.repo_path, '.git')
        if os.path.isdir(git_dir):
            shutil.rmtree(git_dir, ignore_errors=True)

    # ----------------------------- update transaction -----------------------------

    def _lock_path(self):
        return os.path.join(self.repo_path, 'runtime', '.brain-update.lock')

    @contextmanager
    def _update_guard(self):
        """Serialize repository mutations in this process and, on Linux, across
        dashboard processes. The OS releases the file lock if the process dies,
        so a crash cannot leave a stale lock blocking future recovery."""
        if not self._update_lock.acquire(blocking=False):
            yield False
            return

        lock_file = None
        acquired = True
        try:
            if fcntl is not None:
                os.makedirs(os.path.dirname(self._lock_path()), exist_ok=True)
                lock_file = open(self._lock_path(), 'a+')
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    acquired = False
            yield acquired
        finally:
            if lock_file is not None:
                if acquired:
                    try:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
                lock_file.close()
            self._update_lock.release()

    def _busy_response(self):
        return jsonify({
            'success': False,
            'update_in_progress': True,
            'error': self.UPDATE_BUSY_MESSAGE,
        }), 409

    @staticmethod
    def _command_error(result, fallback):
        output = ((result.stderr or '') + '\n' + (result.stdout or '')).strip()
        return output or fallback

    def _verify_commit(self, commit):
        """Verify that an incoming commit and every object reachable from it can
        be read before it is allowed to touch the live checkout."""
        if not commit:
            return False, 'The update source did not provide a commit.'

        exists = self._git('cat-file', '-e', f'{commit}^{{commit}}', timeout=30)
        if exists.returncode != 0:
            return False, self._command_error(
                exists, 'The target commit is missing or unreadable.'
            )

        fsck = self._git(
            'fsck', '--no-dangling', '--no-progress', commit, timeout=180
        )
        if fsck.returncode != 0:
            return False, self._command_error(
                fsck, 'Git object verification failed.'
            )
        return True, ''

    def _fetch_verified(self, remote):
        """Fetch with object validation enabled. Fetch may time out because it
        does not touch the live working tree; the later integrity check prevents
        incomplete objects from being applied."""
        return self._git_durable(
            '-c', 'fetch.fsckObjects=true',
            '-c', 'transfer.fsckObjects=true',
            'fetch', remote, '--recurse-submodules', timeout=300,
        )

    def _git_durable(self, *args, timeout):
        """Run a repository mutation with Git's strongest fsync policy.

        Raspberry Pi installations commonly use SD cards and may be powered off
        without a clean shutdown. Hardening objects, refs, and the index reduces
        the chance of a reported-success update disappearing after power loss.
        """
        return self._git(
            '-c', 'core.fsync=all',
            '-c', 'core.fsyncMethod=fsync',
            *args,
            timeout=timeout,
        )

    def _run_validation_command(self, args, cwd, timeout, label, env=None):
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return False, f'{label} timed out.'
        except OSError as exc:
            return False, f'{label} could not start: {exc}'
        if result.returncode != 0:
            return False, (
                f'{label} failed.\n'
                f'{self._command_error(result, "No command output was produced.")}'
            )
        return True, ''

    def _validate_staged_checkout(self, commit, changed_files):
        """Materialize and validate the incoming commit outside the live tree.

        Git integrity and checkout validation always run. Changed Python files
        are compiled, updater tests run when the updater itself changes, and an
        Angular production build runs when frontend files change.
        """
        parent = os.path.dirname(os.path.realpath(self.repo_path))
        temp_root = tempfile.mkdtemp(prefix='.brain-update-', dir=parent)
        staged = os.path.join(temp_root, 'checkout')
        worktree_added = False
        try:
            self._git('worktree', 'prune', '--expire', 'now', timeout=30)
            checkout = self._git(
                'worktree', 'add', '--detach', staged, commit, timeout=None
            )
            if checkout.returncode != 0:
                return False, (
                    'Could not create the isolated update checkout.\n'
                    f'{self._command_error(checkout, "git worktree add failed")}'
                )
            worktree_added = True

            clean = self._git(
                '-C', staged, 'diff', '--quiet', commit, '--', timeout=60
            )
            if clean.returncode != 0:
                return False, 'The isolated checkout does not match the target commit.'

            python_files = [
                os.path.join(staged, path)
                for path in changed_files
                if path.endswith('.py') and os.path.isfile(os.path.join(staged, path))
            ]
            if python_files:
                ok, error = self._run_validation_command(
                    [sys.executable, '-m', 'py_compile', *python_files],
                    cwd=staged,
                    timeout=180,
                    label='Python compilation',
                )
                if not ok:
                    return False, error

            updater_changed = any(
                path in (
                    'src/dashboard/components/updates.py',
                    'tests/test_updates.py',
                )
                for path in changed_files
            )
            updater_tests = os.path.join(staged, 'tests', 'test_updates.py')
            if (
                updater_changed
                and os.path.isfile(updater_tests)
                and importlib.util.find_spec('pytest') is not None
            ):
                ok, error = self._run_validation_command(
                    [sys.executable, '-m', 'pytest', 'tests/test_updates.py', '-q',
                     '-p', 'no:cacheprovider', '--basetemp',
                     os.path.join(temp_root, 'pytest')],
                    cwd=staged,
                    timeout=300,
                    label='Updater tests',
                )
                if not ok:
                    return False, error

            frontend_changed = any(
                path.startswith('src/dashboard/frontend/')
                for path in changed_files
            )
            if frontend_changed:
                npm = shutil.which('npm')
                live_frontend = os.path.join(
                    self.repo_path, 'src', 'dashboard', 'frontend'
                )
                staged_frontend = os.path.join(
                    staged, 'src', 'dashboard', 'frontend'
                )
                live_modules = os.path.join(live_frontend, 'node_modules')
                staged_modules = os.path.join(staged_frontend, 'node_modules')
                if not npm:
                    return False, 'Frontend verification needs npm.'

                frontend_deps_changed = any(
                    path.endswith('src/dashboard/frontend/package.json')
                    or path.endswith('src/dashboard/frontend/package-lock.json')
                    for path in changed_files
                )
                if frontend_deps_changed:
                    ok, error = self._run_validation_command(
                        [npm, 'ci', '--no-audit', '--no-fund'],
                        cwd=staged_frontend,
                        timeout=1800,
                        label='Frontend dependency installation',
                    )
                    if not ok:
                        return False, error
                elif not os.path.isdir(live_modules):
                    return False, (
                        'Frontend verification needs the installed node_modules '
                        'directory.'
                    )
                elif not os.path.exists(staged_modules):
                    os.symlink(live_modules, staged_modules, target_is_directory=True)

                build_output = os.path.join(temp_root, 'angular-build')
                build_env = dict(os.environ)
                build_env['NG_CLI_ANALYTICS'] = 'false'
                ok, error = self._run_validation_command(
                    [npm, 'run', 'build', '--', '--output-path', build_output],
                    cwd=staged_frontend,
                    timeout=900,
                    label='Angular production build',
                    env=build_env,
                )
                if not ok:
                    return False, error

            return True, ''
        finally:
            if worktree_added:
                self._git(
                    'worktree', 'remove', '--force', staged, timeout=None
                )
            shutil.rmtree(temp_root, ignore_errors=True)
            self._git('worktree', 'prune', '--expire', 'now', timeout=30)

    def _verify_live_checkout(self, commit, changed_files=None):
        current = self._git('rev-parse', 'HEAD', timeout=10)
        if current.returncode != 0 or current.stdout.strip() != commit:
            return False, 'The live checkout did not move to the verified commit.'

        verified, error = self._verify_commit(commit)
        if not verified:
            return False, error

        diff = self._git('diff', '--quiet', commit, '--', timeout=120)
        if diff.returncode != 0:
            return False, (
                'Updated files do not match the verified commit after checkout.'
            )
        return True, ''

    def _sync_live_checkout(self, changed_files):
        """Persist checked-out files before reporting an update as successful.

        Git's ``core.fsync`` policy protects Git objects, refs, and the index,
        but not the live working-tree files written by checkout/merge. On an SD
        card, a restart immediately after a successful response can otherwise
        preserve the new metadata while losing dirty file pages, leaving
        zero-filled source files.
        """
        repo_root = os.path.abspath(self.repo_path)
        directories = {repo_root}
        try:
            for relative_path in changed_files:
                candidate = os.path.abspath(
                    os.path.join(repo_root, relative_path)
                )
                try:
                    inside_repo = os.path.commonpath(
                        [repo_root, candidate]
                    ) == repo_root
                except ValueError:
                    inside_repo = False
                if not inside_repo:
                    return False, (
                        f'Refusing to sync a path outside the repository: '
                        f'{relative_path}'
                    )

                parent = os.path.dirname(candidate)
                while parent and parent != repo_root:
                    directories.add(parent)
                    parent = os.path.dirname(parent)
                directories.add(repo_root)

                if os.path.isfile(candidate) and not os.path.islink(candidate):
                    # Windows rejects fsync on a read-only CRT descriptor;
                    # Linux (the Raspberry Pi target) accepts O_RDONLY.
                    open_mode = os.O_RDWR if os.name == 'nt' else os.O_RDONLY
                    descriptor = os.open(candidate, open_mode)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)

            # Persist directory entries for added, removed, and replaced files.
            directory_flag = getattr(os, 'O_DIRECTORY', None)
            if directory_flag is not None:
                for directory in sorted(
                    directories,
                    key=lambda value: value.count(os.sep),
                    reverse=True,
                ):
                    if not os.path.isdir(directory):
                        continue
                    descriptor = os.open(
                        directory,
                        os.O_RDONLY | directory_flag,
                    )
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)

            # Also flush Git metadata and any filesystem journal records. This
            # call blocks until the kernel has handed all dirty pages to disk.
            sync = getattr(os, 'sync', None)
            if sync is not None:
                sync()
            return True, ''
        except OSError as error:
            return False, f'Could not persist the updated files: {error}'

    def _make_live_checkout_durable(self, commit, changed_files):
        """Verify, fsync, then verify again before the HTTP success response."""
        live_ok, live_error = self._verify_live_checkout(
            commit, changed_files
        )
        if not live_ok:
            return live_ok, live_error

        synced, sync_error = self._sync_live_checkout(changed_files)
        if not synced:
            return False, sync_error

        return self._verify_live_checkout(commit, changed_files)

    def _rollback(
        self,
        previous_head,
        previous_branch='',
        changed_files=None,
    ):
        if previous_branch and previous_branch != 'HEAD':
            result = self._git_durable(
                'checkout', '-f', '-B', previous_branch, previous_head, timeout=None
            )
        else:
            result = self._git_durable(
                'checkout', '-f', '--detach', previous_head, timeout=None
            )
        if result.returncode != 0:
            logger.error(
                'Automatic update rollback failed: %s',
                self._command_error(result, 'git checkout failed'),
            )
            return False
        synced, sync_error = self._sync_live_checkout(changed_files or [])
        if not synced:
            logger.error('Automatic update rollback was not durable: %s', sync_error)
            return False
        return True

    # ----------------------------- github api -----------------------------

    def _parse_github_repo(self, url):
        """Return (owner, repo) for a github.com URL (https/ssh/scp), else None."""
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
        return parts[0], parts[1]

    def _github_get(self, path):
        url = f'{self.GITHUB_API_BASE}{path}'
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/vnd.github+json',
        }
        token = self._load_token()
        if token:
            headers['Authorization'] = f'Bearer {token}'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def _check_via_github(self, gh, head, branch):
        """Read-only update check via the GitHub API (no .git mutation). Returns
        a partial response dict, or None to signal the caller to fall back to
        git (private repo, rate-limited, offline, or local-only HEAD)."""
        owner, repo = gh
        try:
            data = self._github_get(f'/repos/{owner}/{repo}/compare/{head}...{branch}')
        except Exception:
            return None
        if not isinstance(data, dict) or 'status' not in data:
            return None

        # base...head with base=local HEAD, head=remote branch. GitHub reports a
        # status of identical / ahead / behind / diverged:
        #   ahead    -> remote has commits we don't, fast-forwardable (an update)
        #   behind   -> local is ahead of the branch (e.g. on 2027, picking master)
        #   diverged -> both sides have unique commits (needs a force reset)
        status = data.get('status', '')
        ahead_by = data.get('ahead_by', 0)
        commits = data.get('commits') or []
        files = [f.get('filename', '') for f in (data.get('files') or [])]
        diverged = status == 'diverged'
        update_available = status == 'ahead' and ahead_by > 0

        # The actual branch tip. The compare endpoint only lists commits the
        # branch has that we lack, so when we're ahead of / level with it that
        # list is empty -- fetch the real tip so the UI can still offer a switch.
        remote_commit = commits[-1].get('sha', '') if commits else ''
        remote_date = ''
        if commits:
            remote_date = ((commits[-1].get('commit') or {}).get('committer') or {}).get('date', '')
        if not remote_commit:
            try:
                binfo = self._github_get(f'/repos/{owner}/{repo}/branches/{branch}')
                if isinstance(binfo, dict):
                    c = binfo.get('commit') or {}
                    remote_commit = c.get('sha', '') or ''
                    remote_date = ((c.get('commit') or {}).get('committer') or {}).get('date', '') or remote_date
            except Exception:
                remote_commit = ''
        if not remote_commit:
            remote_commit = head
        return {
            'update_available': update_available,
            'diverged': diverged,
            'current_commit': head,
            'current_commit_short': head[:7],
            'remote_commit': remote_commit,
            'remote_commit_short': remote_commit[:7] if remote_commit else '',
            'remote_date': remote_date,
            'behind_by': ahead_by,
            'deps_changed': self._deps_changed(files),
            'message': self.DIVERGED_MESSAGE if diverged else '',
            'via': 'github',
        }

    def _check_via_git(self, remote, branch, head):
        """Update check via git fetch (works for private repos through the
        deploy key, and any provider)."""
        fetch = self._fetch_verified(remote)
        if fetch.returncode != 0:
            auth_required = self._is_auth_error(fetch.stderr or fetch.stdout)
            return {
                'update_available': False,
                'current_commit': head,
                'current_commit_short': head[:7],
                'remote_commit': '',
                'remote_commit_short': '',
                'auth_required': auth_required,
                'message': (self.AUTH_REQUIRED_MESSAGE if auth_required
                            else 'Could not reach the configured repository.'),
                'via': 'git',
            }
        remote_branch = f'{remote}/{branch}'
        remote_commit = self._git('rev-parse', remote_branch, timeout=10).stdout.strip()
        merge_base = self._git('merge-base', 'HEAD', remote_branch, timeout=10).stdout.strip()
        # Fast-forwardable: remote is strictly ahead of local (merge-base == HEAD).
        update_available = bool(remote_commit) and merge_base == head and remote_commit != head
        # Diverged: both sides have unique commits (merge-base is neither tip).
        # Common when switching the source to a fork with its own history -- a
        # plain pull can't fast-forward, so the force reset is the way across.
        diverged = (bool(remote_commit) and remote_commit != head
                    and merge_base != head and merge_base != remote_commit)

        files = self._changed_files(head, remote_commit) if update_available else []
        behind_by = 0
        if remote_commit:
            counts = self._git('rev-list', '--left-right', '--count',
                               f'HEAD...{remote_branch}', timeout=15)
            if counts.returncode == 0:
                parts = counts.stdout.split()
                if len(parts) == 2 and parts[1].isdigit():
                    behind_by = int(parts[1])

        remote_date = ''
        if remote_commit:
            d = self._git('show', '-s', '--format=%cI', remote_commit, timeout=10)
            if d.returncode == 0:
                remote_date = d.stdout.strip()

        return {
            'update_available': update_available,
            'diverged': diverged,
            'current_commit': head,
            'current_commit_short': head[:7],
            'remote_commit': remote_commit,
            'remote_commit_short': remote_commit[:7] if remote_commit else '',
            'remote_date': remote_date,
            'behind_by': behind_by,
            'deps_changed': self._deps_changed(files),
            'message': self.DIVERGED_MESSAGE if diverged else '',
            'via': 'git',
        }

    # ----------------------------- check -----------------------------

    def handle_check(self):
        """Check whether an update is available from the configured source."""
        with self._update_guard() as acquired:
            if not acquired:
                return self._busy_response()
            return self._handle_check_locked()

    def _handle_check_locked(self):
        try:
            if not self._is_git_repo():
                cfg = self._load_config()
                return jsonify({
                    'success': True,
                    'is_git_repo': False,
                    'update_available': False,
                    'source': cfg.get('url') or '',
                    'configured_branch': cfg.get('branch') or '',
                })

            cfg = self._load_config()
            remote, err = self._ensure_configured_remote(cfg)
            if err:
                return jsonify({'success': False, 'error': err}), 400

            head = self._git('rev-parse', 'HEAD', timeout=10).stdout.strip()
            valid_head = self._git(
                'cat-file', '-e', f'{head}^{{commit}}', timeout=30
            )
            if not head or valid_head.returncode != 0:
                return jsonify({
                    'success': False,
                    'is_git_repo': True,
                    'repository_corrupt': True,
                    'error': self.CORRUPT_REPO_MESSAGE,
                }), 500

            branch = self._resolve_branch(cfg, remote)
            source = self._source_label(cfg)

            response = None
            gh = self._parse_github_repo(cfg.get('url') or self._origin_url())
            if gh:
                response = self._check_via_github(gh, head, branch)
            if response is None:
                response = self._check_via_git(remote, branch, head)

            response.update({
                'success': True,
                'is_git_repo': True,
                'branch': branch,
                'source': source,
                'remote': source,
                'remote_branch': branch,
            })
            return jsonify(response)
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Command timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- pull (fast-forward) -----------------------------

    def _collect_conflict(self, head, remote_branch, merge_result):
        """Build a browser-friendly description of why an update could not be
        fast-forwarded, listing the files involved (#2)."""
        raw = (merge_result.stderr or merge_result.stdout or '').strip()
        diverged = 'fast-forward' in raw.lower()

        files = []
        status = self._git('status', '--porcelain', timeout=10)
        if status.returncode == 0:
            files = [line[3:].strip() for line in status.stdout.splitlines() if line.strip()]
        if not files:
            files = self._changed_files(head, remote_branch)

        if diverged:
            message = ('Your branch has diverged from the update source and cannot be '
                       'fast-forwarded. Review the files below, or use "Discard local '
                       'changes & update" to overwrite local work with the update.')
        else:
            message = ('Local changes would be overwritten by the update. Review the files '
                       'below, or use "Discard local changes & update".')
        return {'files': files, 'raw': raw, 'diverged': diverged, 'message': message}

    def _fetch_failure_response(self, fetch):
        """Build the JSON response for a failed fetch, distinguishing a private
        repo / auth problem (so the UI can show setup instructions) from a
        generic network error."""
        output = fetch.stderr or fetch.stdout
        if self._is_permission_error(output):
            return jsonify({
                'success': False,
                'error': self.PERMISSION_ERROR_MESSAGE,
            }), 500
        if self._is_auth_error(output):
            return jsonify({
                'success': False,
                'auth_required': True,
                'error': self.AUTH_REQUIRED_MESSAGE,
            }), 401
        return jsonify({
            'success': False,
            'error': f'Failed to fetch from the configured repository.\n{fetch.stderr.strip()}'
        }), 500

    def handle_pull(self):
        """Fast-forward the codebase to the configured remote branch."""
        with self._update_guard() as acquired:
            if not acquired:
                return self._busy_response()
            return self._handle_pull_locked()

    def _handle_pull_locked(self):
        try:
            if not self._is_git_repo():
                return jsonify({
                    'success': False,
                    'is_git_repo': False,
                    'error': 'This installation is not a git repository. Use "Set up updates" first.'
                }), 400

            cfg = self._load_config()
            remote, err = self._ensure_configured_remote(cfg)
            if err:
                return jsonify({'success': False, 'error': err}), 400

            branch = self._resolve_branch(cfg, remote)
            head = self._git('rev-parse', 'HEAD', timeout=10).stdout.strip()
            current_branch = self._git(
                'rev-parse', '--abbrev-ref', 'HEAD', timeout=10
            ).stdout.strip()

            valid_head, integrity_error = self._verify_commit(head)
            if not valid_head:
                logger.error('Local Git integrity check failed: %s', integrity_error)
                return jsonify({
                    'success': False,
                    'repository_corrupt': True,
                    'error': self.CORRUPT_REPO_MESSAGE,
                }), 500

            status = self._git(
                'status', '--porcelain', '--untracked-files=no', timeout=30
            )
            if status.returncode != 0:
                return jsonify({
                    'success': False,
                    'repository_corrupt': True,
                    'error': self.CORRUPT_REPO_MESSAGE,
                }), 500
            if status.stdout.strip():
                files = [
                    line[3:].strip()
                    for line in status.stdout.splitlines()
                    if line.strip()
                ]
                return jsonify({
                    'success': False,
                    'conflict': {
                        'files': files,
                        'raw': status.stdout.strip(),
                        'diverged': False,
                        'message': (
                            'Tracked files have local changes. Commit them first, '
                            'or use "Discard local changes & update".'
                        ),
                    },
                    'error': (
                        'Tracked files have local changes. Commit them first, or '
                        'use "Discard local changes & update".'
                    ),
                }), 409

            fetch = self._fetch_verified(remote)
            if fetch.returncode != 0:
                logger.error(
                    'Verified update fetch failed: %s',
                    self._command_error(fetch, 'git fetch failed'),
                )
                return self._fetch_failure_response(fetch)

            remote_branch = f'{remote}/{branch}'
            remote_ref = self._git('rev-parse', remote_branch, timeout=10)
            remote_commit = remote_ref.stdout.strip()
            valid_target, integrity_error = self._verify_commit(remote_commit)
            if remote_ref.returncode != 0 or not valid_target:
                logger.error('Incoming Git integrity check failed: %s', integrity_error)
                return jsonify({
                    'success': False,
                    'verification_failed': True,
                    'error': (
                        'The downloaded update failed Git integrity checks. '
                        'The live code was not changed.'
                    ),
                }), 502

            changed_files = self._changed_files(head, remote_commit)
            staged_ok, staged_error = self._validate_staged_checkout(
                remote_commit, changed_files
            )
            if not staged_ok:
                logger.error('Staged update verification failed: %s', staged_error)
                return jsonify({
                    'success': False,
                    'verification_failed': True,
                    'error': (
                        'The update failed isolated verification. '
                        f'The live code was not changed.\n{staged_error}'
                    ),
                }), 422

            # Do not impose a timeout while Git is writing the live checkout.
            # Killing checkout mid-write is worse than waiting for it to finish.
            merge = self._git_durable(
                'merge', '--ff-only', remote_branch, timeout=None
            )
            if merge.returncode != 0:
                conflict = self._collect_conflict(head, remote_branch, merge)
                return jsonify({
                    'success': False,
                    'conflict': conflict,
                    'error': conflict['message']
                }), 409

            submodules = self._git_durable(
                'submodule', 'update', '--init', '--recursive', timeout=None
            )
            live_ok, live_error = self._make_live_checkout_durable(
                remote_commit, changed_files
            )
            if submodules.returncode != 0:
                live_ok = False
                live_error = (
                    'Submodule update failed.\n'
                    f'{self._command_error(submodules, "git submodule update failed")}'
                )

            if not live_ok:
                rolled_back = self._rollback(
                    head,
                    current_branch,
                    changed_files,
                )
                logger.error(
                    'Live update verification failed (rollback=%s): %s',
                    rolled_back,
                    live_error,
                )
                return jsonify({
                    'success': False,
                    'verification_failed': True,
                    'rolled_back': rolled_back,
                    'error': (
                        'The live checkout failed verification and '
                        f'{"was rolled back." if rolled_back else "could not be rolled back."}\n'
                        f'{live_error}'
                    ),
                }), 500

            deps_changed = self._deps_changed(changed_files)
            return jsonify({
                'success': True,
                'deps_changed': deps_changed,
                'message': self._success_message(deps_changed)
            })
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Update timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def _success_message(deps_changed, forced=False):
        base = ('Local changes discarded and update applied.' if forced
                else 'Update successful!')
        msg = (
            f'{base} Updated files are safely stored. '
            'Please restart the application for changes to take effect.'
        )
        if deps_changed:
            msg += (' Dependencies changed -- reinstall them (pip install -r requirements.txt, '
                    'and npm install in src/dashboard/frontend) before restarting.')
        return msg

    # ----------------------------- force pull -----------------------------

    def handle_force_pull(self):
        """Discard local changes and switch onto the configured remote branch.

        Used both to recover when a plain fast-forward is blocked (runtime/ files
        the app rewrites are tracked) and to switch branches. We ``checkout -f -B
        <branch> <remote>/<branch>`` rather than ``reset --hard`` so the checkout
        actually lands *on* the tracked branch (git reports the right branch) and
        the previously checked-out branch ref is left untouched. Destructive --
        the frontend gates this behind an explicit confirmation."""
        with self._update_guard() as acquired:
            if not acquired:
                return self._busy_response()
            return self._handle_force_pull_locked()

    def _handle_force_pull_locked(self):
        try:
            if not self._is_git_repo():
                return jsonify({'success': False, 'error': 'This installation is not a git repository.'}), 400

            cfg = self._load_config()
            remote, err = self._ensure_configured_remote(cfg)
            if err:
                return jsonify({'success': False, 'error': err}), 400

            branch = self._resolve_branch(cfg, remote)
            head = self._git('rev-parse', 'HEAD', timeout=10).stdout.strip()
            current_branch = self._git(
                'rev-parse', '--abbrev-ref', 'HEAD', timeout=10
            ).stdout.strip()

            valid_head, integrity_error = self._verify_commit(head)
            if not valid_head:
                logger.error('Local Git integrity check failed: %s', integrity_error)
                return jsonify({
                    'success': False,
                    'repository_corrupt': True,
                    'error': self.CORRUPT_REPO_MESSAGE,
                }), 500

            fetch = self._fetch_verified(remote)
            if fetch.returncode != 0:
                logger.error(
                    'Verified force-update fetch failed: %s',
                    self._command_error(fetch, 'git fetch failed'),
                )
                return self._fetch_failure_response(fetch)

            remote_branch = f'{remote}/{branch}'
            remote_ref = self._git('rev-parse', remote_branch, timeout=10)
            remote_commit = remote_ref.stdout.strip()
            valid_target, integrity_error = self._verify_commit(remote_commit)
            if remote_ref.returncode != 0 or not valid_target:
                logger.error('Incoming Git integrity check failed: %s', integrity_error)
                return jsonify({
                    'success': False,
                    'verification_failed': True,
                    'error': (
                        'The downloaded update failed Git integrity checks. '
                        'The live code was not changed.'
                    ),
                }), 502

            changed_files = self._changed_files(head, remote_commit)
            staged_ok, staged_error = self._validate_staged_checkout(
                remote_commit, changed_files
            )
            if not staged_ok:
                logger.error('Staged force-update verification failed: %s', staged_error)
                return jsonify({
                    'success': False,
                    'verification_failed': True,
                    'error': (
                        'The update failed isolated verification. '
                        f'The live code was not changed.\n{staged_error}'
                    ),
                }), 422

            # -f discards local working-tree changes; -B creates/resets the local
            # branch at the remote tip and checks it out (so HEAD is on `branch`).
            checkout = self._git_durable(
                'checkout', '-f', '-B', branch, remote_branch, timeout=None
            )
            if checkout.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Failed to switch to the update.\n{checkout.stderr.strip()}'
                }), 500

            submodules = self._git_durable(
                'submodule', 'update', '--init', '--recursive', timeout=None
            )
            live_ok, live_error = self._make_live_checkout_durable(
                remote_commit, changed_files
            )
            if submodules.returncode != 0:
                live_ok = False
                live_error = (
                    'Submodule update failed.\n'
                    f'{self._command_error(submodules, "git submodule update failed")}'
                )

            if not live_ok:
                rolled_back = self._rollback(
                    head,
                    current_branch,
                    changed_files,
                )
                logger.error(
                    'Live force-update verification failed (rollback=%s): %s',
                    rolled_back,
                    live_error,
                )
                return jsonify({
                    'success': False,
                    'verification_failed': True,
                    'rolled_back': rolled_back,
                    'error': (
                        'The live checkout failed verification and '
                        f'{"was rolled back." if rolled_back else "could not be rolled back."}\n'
                        f'{live_error}'
                    ),
                }), 500

            deps_changed = self._deps_changed(changed_files)
            return jsonify({
                'success': True,
                'deps_changed': deps_changed,
                'message': self._success_message(deps_changed, forced=True)
            })
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Update timed out'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- adopt (ZIP install) -----------------------------

    def _adopt_preflight(self):
        """Fail clearly when the dashboard user can't own the files, instead of
        letting git error out cryptically mid-way (#6)."""
        if not os.path.isdir(self.repo_path):
            return 'Repository path does not exist.'
        if not os.access(self.repo_path, os.W_OK):
            return (f'No write permission for {self.repo_path}. The dashboard user must own '
                    f'these files (check ownership / re-extract as the right user).')
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            try:
                st = os.stat(self.repo_path)
                if st.st_uid != os.geteuid():
                    return (f'{self.repo_path} is owned by uid {st.st_uid} but the dashboard '
                            f'runs as uid {os.geteuid()}. Fix ownership (e.g. chown) before '
                            f'setting up updates.')
            except OSError:
                pass
        return None

    def handle_adopt(self):
        """Turn a non-git install (e.g. a downloaded ZIP) into a git-tracked
        clone of the configured repo so future updates use the normal flow."""
        with self._update_guard() as acquired:
            if not acquired:
                return self._busy_response()
            return self._handle_adopt_locked()

    def _handle_adopt_locked(self):
        try:
            if self._is_git_repo():
                return jsonify({'success': False, 'error': 'This installation is already a git repository.'}), 400

            cfg = self._load_config()
            url = cfg.get('url', '')
            ok, err = self._validate_repo_url(url)
            if not ok:
                return jsonify({
                    'success': False,
                    'error': err or 'Set a repository URL first (use the pencil next to the title).'
                }), 400

            perm_err = self._adopt_preflight()
            if perm_err:
                return jsonify({'success': False, 'error': perm_err}), 403

            remote = cfg['remote_name']
            branch = ''
            try:
                init = self._git('init', timeout=30)
                if init.returncode != 0:
                    raise RuntimeError(init.stderr.strip() or 'git init failed')

                add = self._git('remote', 'add', remote, self._effective_url(url), timeout=10)
                if add.returncode != 0:
                    raise RuntimeError(add.stderr.strip() or 'failed to add remote')

                fetch = self._fetch_verified(remote)
                if fetch.returncode != 0:
                    if self._is_auth_error(fetch.stderr or fetch.stdout):
                        self._cleanup_git_dir()
                        return jsonify({
                            'success': False,
                            'auth_required': True,
                            'error': self.AUTH_REQUIRED_MESSAGE,
                        }), 401
                    raise RuntimeError(fetch.stderr.strip() or 'failed to fetch repository')

                branch = self._resolve_branch(cfg, remote)
                remote_ref = f'{remote}/{branch}'
                remote_commit = self._git(
                    'rev-parse', remote_ref, timeout=10
                ).stdout.strip()
                valid_target, integrity_error = self._verify_commit(remote_commit)
                if not valid_target:
                    raise RuntimeError(
                        f'incoming Git integrity check failed: {integrity_error}'
                    )

                tree = self._git(
                    'ls-tree', '-r', '--name-only', remote_commit, timeout=60
                )
                if tree.returncode != 0:
                    raise RuntimeError(
                        self._command_error(tree, 'failed to list incoming files')
                    )
                changed_files = [
                    line.strip()
                    for line in tree.stdout.splitlines()
                    if line.strip()
                ]
                staged_ok, staged_error = self._validate_staged_checkout(
                    remote_commit, changed_files
                )
                if not staged_ok:
                    raise RuntimeError(
                        f'isolated update verification failed: {staged_error}'
                    )

                reset = self._git_durable(
                    'reset', '--hard', remote_ref, timeout=None
                )
                if reset.returncode != 0:
                    raise RuntimeError(reset.stderr.strip() or 'failed to check out repository')

                submodules = self._git_durable(
                    'submodule', 'update', '--init', '--recursive', timeout=None
                )
                if submodules.returncode != 0:
                    raise RuntimeError(
                        self._command_error(
                            submodules, 'failed to update submodules'
                        )
                    )
                live_ok, live_error = self._make_live_checkout_durable(
                    remote_commit,
                    changed_files,
                )
                if not live_ok:
                    raise RuntimeError(
                        f'live checkout verification failed: {live_error}'
                    )
            except Exception as inner:
                self._cleanup_git_dir()
                return jsonify({
                    'success': False,
                    'error': f'Setup failed and was rolled back: {inner}'
                }), 500

            return jsonify({
                'success': True,
                'message': (f'Updates configured from {url} (branch {branch}). '
                            f'Please restart the application.')
            })
        except subprocess.TimeoutExpired:
            self._cleanup_git_dir()
            return jsonify({'success': False, 'error': 'Setup timed out and was rolled back.'}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- branches -----------------------------

    def handle_list_branches(self):
        """List branches on the configured source so the student can choose one
        to track (#4). GitHub API for public repos, git fallback otherwise."""
        try:
            cfg = self._load_config()
            url = cfg.get('url') or self._origin_url()
            branches = []
            default_branch = ''

            gh = self._parse_github_repo(url)
            if gh:
                owner, repo = gh
                try:
                    info = self._github_get(f'/repos/{owner}/{repo}')
                    if isinstance(info, dict):
                        default_branch = info.get('default_branch', '') or ''
                    data = self._github_get(f'/repos/{owner}/{repo}/branches?per_page=100')
                    if isinstance(data, list):
                        branches = [b.get('name') for b in data if b.get('name')]
                except Exception:
                    branches = []

            if not branches and self._is_git_repo():
                remote, err = self._ensure_configured_remote(cfg)
                if not err:
                    ls = self._git('ls-remote', '--heads', remote, timeout=30)
                    if ls.returncode == 0:
                        for line in ls.stdout.splitlines():
                            if '\trefs/heads/' in line:
                                branches.append(line.split('\trefs/heads/')[1].strip())
                    if not default_branch:
                        # The repo's real default -- not the tracked branch, so a
                        # tracked branch isn't mislabeled "(default)".
                        default_branch = self._remote_default_branch(remote)

            return jsonify({
                'success': True,
                'branches': sorted(set(b for b in branches if b)),
                'default_branch': default_branch,
                'selected_branch': cfg.get('branch') or default_branch,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- source (repo URL) -----------------------------

    def handle_get_source(self):
        """Report the currently configured update source so the student can see
        and change which repository the car pulls updates from (e.g. their own
        fork). An empty url means updates come from ``origin`` (the repo that was
        cloned), or that none is set yet for a ZIP install."""
        try:
            cfg = self._load_config()
            origin = self._origin_url() if self._is_git_repo() else ''
            return jsonify({
                'success': True,
                'url': cfg.get('url') or '',
                'branch': cfg.get('branch') or '',
                'remote_name': cfg.get('remote_name') or self.DEFAULT_REMOTE_NAME,
                'origin_url': origin,
                'is_git_repo': self._is_git_repo(),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_set_source(self, url):
        """Persist the repository URL the student wants to pull updates from.

        An empty url is allowed and resets the source back to ``origin`` (the
        repo that was cloned). A non-empty url is validated the same way as the
        adopt flow. Changing the url leaves the configured remote to be
        re-pointed lazily on the next check via ``_ensure_configured_remote``."""
        try:
            url = (url or '').strip()
            if url:
                ok, err = self._validate_repo_url(url)
                if not ok:
                    return jsonify({'success': False, 'error': err}), 400

            cfg = self._load_config()
            cfg['url'] = url
            self._save_config(cfg)

            # Re-point the configured remote immediately when we can, so the next
            # check/pull uses the new url even before a fetch happens.
            if url and self._is_git_repo():
                self._ensure_configured_remote(cfg)

            message = (f'Update source set to {url}.' if url
                       else 'Update source reset to the original repository (origin).')
            return jsonify({'success': True, 'url': url, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ----------------------------- access token (private repos) -----------------------------

    def handle_get_token(self):
        """Report whether a private-repo access token is configured. The token
        itself is never returned."""
        try:
            return jsonify({'success': True, 'has_token': self._has_token()})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_set_token(self, token):
        """Store a read-only token for reaching a private update repo, verifying
        it can actually read the configured remote before saving."""
        try:
            tok = (token or '').strip()
            if not tok:
                return jsonify({'success': False, 'error': 'Paste an access token first.'}), 400

            # Verify with a token-authenticated ls-remote against the configured
            # source (works for any host, not just GitHub).
            cfg = self._load_config()
            url = self._effective_url(cfg.get('url') or self._origin_url())
            if not url:
                return jsonify({'success': False, 'error': 'Set a repository URL first.'}), 400

            basic = base64.b64encode(f'x-access-token:{tok}'.encode()).decode()
            env = dict(os.environ)
            env['GIT_TERMINAL_PROMPT'] = '0'
            env['GIT_ASKPASS'] = env.get('GIT_ASKPASS', '') or 'echo'
            probe = subprocess.run(
                ['git', '-c', f'http.extraHeader=Authorization: Basic {basic}',
                 'ls-remote', '--heads', url],
                cwd=self.repo_path, capture_output=True, text=True, timeout=30, env=env,
            )
            if probe.returncode != 0:
                if self._is_auth_error(probe.stderr or probe.stdout):
                    return jsonify({'success': False, 'error': "That token can't read this repository. Check it has Contents: read access."}), 400
                return jsonify({'success': False, 'error': f'Could not verify the token.\n{probe.stderr.strip()}'}), 502

            os.makedirs(self._key_dir(), exist_ok=True)
            fd = os.open(self._token_path(), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, (tok + '\n').encode())
            finally:
                os.close(fd)
            try:
                os.chmod(self._token_path(), 0o600)
            except OSError:
                pass

            # Re-point the remote to https now that the token can authenticate it.
            if cfg.get('url') and self._is_git_repo():
                self._ensure_configured_remote(cfg)

            return jsonify({'success': True, 'has_token': True,
                            'message': 'Access token saved and verified.'})
        except subprocess.TimeoutExpired:
            return jsonify({'success': False, 'error': 'Verifying the token timed out.'}), 504
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

    def handle_set_branch(self, branch):
        """Persist the branch the student wants to track (#4)."""
        try:
            branch = (branch or '').strip()
            if branch.startswith('-') or any(c.isspace() for c in branch):
                return jsonify({'success': False, 'error': 'Invalid branch name.'}), 400

            cfg = self._load_config()
            cfg['branch'] = branch
            self._save_config(cfg)

            message = (f'Update branch set to "{branch}".' if branch
                       else 'Update branch reset to the repository default.')
            return jsonify({'success': True, 'selected_branch': branch, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
