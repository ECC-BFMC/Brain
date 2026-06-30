import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urlparse

from flask import jsonify


class UpdateManager:
    """Handles Brain codebase updates from a configurable git remote.

    The dashboard never stores or transmits credentials. The update source is
    configured out-of-band on the Pi via ``runtime/update_config.json`` together
    with the student's own git auth (an SSH deploy key or a credential helper set
    up over SSH). The GitHub API is used only for the read-only check / branch
    listing layer, with a git fallback for private, non-GitHub, rate-limited or
    offline repositories. Applying an update is always git (fetch + fast-forward,
    or an explicit force reset) -- never the API tarball, so no token is needed.
    """

    DEFAULT_REMOTE_NAME = 'bfmc-upstream'
    GITHUB_API_BASE = 'https://api.github.com'
    USER_AGENT = 'BFMC-Brain'

    def __init__(self, repo_path):
        self.repo_path = repo_path

    # ----------------------------- config -----------------------------

    def _config_path(self):
        return os.path.join(self.repo_path, 'runtime', 'update_config.json')

    def _load_config(self):
        """Read the Pi-side update config. Defaults keep zero-config behaviour:
        an empty url means "update from origin" (the repo the student cloned)."""
        cfg = {'remote_name': self.DEFAULT_REMOTE_NAME, 'url': '', 'branch': ''}
        path = self._config_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cfg['remote_name'] = str(data.get('remote_name') or cfg['remote_name']).strip()
                    cfg['url'] = str(data.get('url') or '').strip()
                    cfg['branch'] = str(data.get('branch') or '').strip()
            except (ValueError, OSError):
                pass
        return cfg

    def _save_config(self, cfg):
        path = self._config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(cfg, f, indent=2)

    # ----------------------------- deploy key -----------------------------

    def _key_dir(self):
        # git-ignored, untracked -> survives `git reset --hard` during updates.
        return os.path.join(self.repo_path, 'runtime', 'update_keys')

    def _key_path(self):
        return os.path.join(self._key_dir(), 'deploy_key')

    def _pub_key_path(self):
        return self._key_path() + '.pub'

    def _has_deploy_key(self):
        return os.path.exists(self._key_path())

    def _ssh_command(self):
        """The ssh command git should use. When a dashboard-managed deploy key
        exists, pin git to exactly that key; otherwise fall back to the agent /
        default keys. BatchMode keeps git from ever blocking on a prompt."""
        base = 'ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new'
        if self._has_deploy_key():
            # Quote the path (Windows dev paths contain spaces); IdentitiesOnly
            # stops ssh from offering other keys first and tripping MaxAuthTries.
            return f'{base} -o IdentitiesOnly=yes -i "{self._key_path()}"'
        return base

    # ----------------------------- git helpers -----------------------------

    def _git(self, *args, timeout=30):
        # Force git to fail fast instead of blocking on an interactive
        # credential / passphrase prompt when a private repo has no auth set up
        # on the Pi. Without these, an https private URL can hang until the
        # subprocess timeout, and an ssh key with a passphrase can stall too.
        env = dict(os.environ)
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = env.get('GIT_ASKPASS', '') or 'echo'
        env['GIT_SSH_COMMAND'] = self._ssh_command()
        return subprocess.run(
            ['git', *args],
            cwd=self.repo_path,
            capture_output=True, text=True, timeout=timeout, env=env
        )

    @staticmethod
    def _to_ssh_url(url):
        """Convert an http(s) git URL to its scp-style SSH form so a deploy key
        can be used (keys only authenticate over SSH). Non-http URLs and ones we
        can't parse are returned unchanged."""
        u = (url or '').strip()
        if u.startswith('http://') or u.startswith('https://'):
            parsed = urlparse(u)
            host = parsed.hostname or ''
            path = parsed.path.lstrip('/')
            if host and path:
                if not path.endswith('.git'):
                    path += '.git'
                return f'git@{host}:{path}'
        return u

    def _effective_url(self, url):
        """The URL git should actually use.

        A deploy key only helps over SSH, and GitHub *rejects anonymous SSH even
        for public repos* -- so blindly switching every URL to SSH would make a
        public repo demand a key it doesn't need. Only rewrite to SSH when a key
        exists AND the repo isn't publicly reachable (i.e. it actually needs
        auth). Public repos keep their https URL and clone anonymously."""
        if url and self._has_deploy_key() and not self._repo_is_public(url):
            return self._to_ssh_url(url)
        return url

    def _repo_is_public(self, url):
        """Best-effort: True only if GitHub confirms the repo is public (an
        unauthenticated API lookup succeeds with private == False). Anything we
        can't confirm (non-GitHub, private, offline, rate-limited) returns False,
        so the deploy key is used as the safe default."""
        gh = self._parse_github_repo(url)
        if not gh:
            return False
        owner, repo = gh
        try:
            info = self._github_get(f'/repos/{owner}/{repo}')
        except Exception:
            return False
        return isinstance(info, dict) and info.get('private') is False

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
        "Couldn't access this repository. It looks private, and the car has no "
        "credentials for it yet. Grant the Pi read access, then try again."
    )

    DIVERGED_MESSAGE = (
        "The update source has a different history than this car's copy (common "
        "when switching to a fork). Use \"Discard local changes & update\" to "
        "switch to it -- this overwrites local changes to tracked files."
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

    def _resolve_branch(self, cfg, remote):
        """Configured branch, else the remote's default branch (never hardcode
        master, since forks may use main or anything else)."""
        if cfg.get('branch'):
            return cfg['branch']
        symref = self._git('ls-remote', '--symref', remote, 'HEAD', timeout=20)
        if symref.returncode == 0:
            for line in symref.stdout.splitlines():
                if line.startswith('ref:'):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].startswith('refs/heads/'):
                        return parts[1][len('refs/heads/'):]
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
            if os.path.basename(f) == 'requirements.txt' or f.endswith('frontend/package.json'):
                return True
        return False

    def _cleanup_git_dir(self):
        git_dir = os.path.join(self.repo_path, '.git')
        if os.path.isdir(git_dir):
            shutil.rmtree(git_dir, ignore_errors=True)

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
        req = urllib.request.Request(url, headers={
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/vnd.github+json',
        })
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
        fetch = self._git('fetch', remote, timeout=60)
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
        if self._is_auth_error(fetch.stderr or fetch.stdout):
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

            fetch = self._git('fetch', remote, '--recurse-submodules', timeout=120)
            if fetch.returncode != 0:
                return self._fetch_failure_response(fetch)

            remote_branch = f'{remote}/{branch}'
            remote_commit = self._git('rev-parse', remote_branch, timeout=10).stdout.strip()

            merge = self._git('merge', '--ff-only', remote_branch, timeout=120)
            if merge.returncode != 0:
                conflict = self._collect_conflict(head, remote_branch, merge)
                return jsonify({
                    'success': False,
                    'conflict': conflict,
                    'error': conflict['message']
                }), 409

            self._git('submodule', 'update', '--init', '--recursive', timeout=180)
            deps_changed = self._deps_changed(self._changed_files(head, remote_commit))
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
        msg = f'{base} Please restart the application for changes to take effect.'
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
        try:
            if not self._is_git_repo():
                return jsonify({'success': False, 'error': 'This installation is not a git repository.'}), 400

            cfg = self._load_config()
            remote, err = self._ensure_configured_remote(cfg)
            if err:
                return jsonify({'success': False, 'error': err}), 400

            branch = self._resolve_branch(cfg, remote)
            head = self._git('rev-parse', 'HEAD', timeout=10).stdout.strip()

            fetch = self._git('fetch', remote, '--recurse-submodules', timeout=120)
            if fetch.returncode != 0:
                return self._fetch_failure_response(fetch)

            remote_branch = f'{remote}/{branch}'
            remote_commit = self._git('rev-parse', remote_branch, timeout=10).stdout.strip()

            # -f discards local working-tree changes; -B creates/resets the local
            # branch at the remote tip and checks it out (so HEAD is on `branch`).
            checkout = self._git('checkout', '-f', '-B', branch, remote_branch, timeout=60)
            if checkout.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Failed to switch to the update.\n{checkout.stderr.strip()}'
                }), 500

            self._git('submodule', 'update', '--init', '--recursive', timeout=180)
            deps_changed = self._deps_changed(self._changed_files(head, remote_commit))
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
        try:
            if self._is_git_repo():
                return jsonify({'success': False, 'error': 'This installation is already a git repository.'}), 400

            cfg = self._load_config()
            url = cfg.get('url', '')
            ok, err = self._validate_repo_url(url)
            if not ok:
                return jsonify({
                    'success': False,
                    'error': err or 'Set a repository URL in runtime/update_config.json first.'
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

                fetch = self._git('fetch', remote, '--recurse-submodules', timeout=300)
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
                reset = self._git('reset', '--hard', f'{remote}/{branch}', timeout=120)
                if reset.returncode != 0:
                    raise RuntimeError(reset.stderr.strip() or 'failed to check out repository')

                self._git('submodule', 'update', '--init', '--recursive', timeout=300)
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
                        default_branch = self._resolve_branch(cfg, remote)

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

    # ----------------------------- deploy key (private repos) -----------------------------

    def _key_fingerprint(self):
        pub = self._pub_key_path()
        if not os.path.exists(pub):
            return ''
        try:
            res = subprocess.run(['ssh-keygen', '-lf', pub],
                                 capture_output=True, text=True, timeout=10,
                                 stdin=subprocess.DEVNULL)
            return res.stdout.strip() if res.returncode == 0 else ''
        except Exception:
            return ''

    def handle_get_key(self):
        """Report whether a deploy key is configured and, if so, the matching
        public key (so the student can add it to their repo's Deploy Keys). The
        private key is never returned."""
        try:
            has_key = self._has_deploy_key()
            public_key = ''
            if os.path.exists(self._pub_key_path()):
                with open(self._pub_key_path(), 'r') as f:
                    public_key = f.read().strip()
            return jsonify({
                'success': True,
                'has_key': has_key,
                'public_key': public_key,
                'fingerprint': self._key_fingerprint() if has_key else '',
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_generate_key(self):
        """Generate a fresh SSH deploy key directly on the car. The private key
        never leaves the device; the caller gets back only the public key to add
        to the repo's Deploy Keys. This is the preferred flow (more secure than
        pasting a key generated elsewhere)."""
        try:
            os.makedirs(self._key_dir(), exist_ok=True)
            key_path = self._key_path()
            # Remove any existing key first so ssh-keygen doesn't block on an
            # interactive "overwrite?" prompt.
            for p in (key_path, self._pub_key_path()):
                if os.path.exists(p):
                    os.remove(p)
            try:
                res = subprocess.run(
                    ['ssh-keygen', '-t', 'ed25519', '-f', key_path,
                     '-N', '', '-C', 'bfmc-deploy', '-q'],
                    capture_output=True, text=True, timeout=30,
                    stdin=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                return jsonify({'success': False, 'error': 'ssh-keygen is not installed on this device.'}), 500
            except subprocess.TimeoutExpired:
                return jsonify({'success': False, 'error': 'Key generation timed out.'}), 500
            if res.returncode != 0:
                return jsonify({'success': False, 'error': res.stderr.strip() or 'Key generation failed.'}), 500

            try:
                os.chmod(key_path, 0o600)
            except OSError:
                pass

            pub = ''
            if os.path.exists(self._pub_key_path()):
                with open(self._pub_key_path(), 'r') as f:
                    pub = f.read().strip()

            # Re-point the remote to the SSH form now that a key exists.
            cfg = self._load_config()
            if cfg.get('url') and self._is_git_repo():
                self._ensure_configured_remote(cfg)

            return jsonify({
                'success': True,
                'has_key': True,
                'public_key': pub,
                'fingerprint': self._key_fingerprint(),
                'message': ('Deploy key generated on the car. Add the public key below to your '
                            'repository (Settings -> Deploy keys), then check for updates.'),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_delete_key(self):
        """Remove the configured deploy key (revert to default/agent auth)."""
        try:
            for path in (self._key_path(), self._pub_key_path()):
                if os.path.exists(path):
                    os.remove(path)
            return jsonify({'success': True, 'has_key': False, 'message': 'Deploy key removed.'})
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
