import subprocess
from flask import jsonify


class UpdateManager:
    """Handles codebase updates from the official BFMC Brain repository."""

    OFFICIAL_REPO_URL = 'https://github.com/ECC-BFMC/Brain.git'
    OFFICIAL_REMOTE_NAME = 'bfmc-official'

    def __init__(self, repo_path):
        self.repo_path = repo_path

    def _validate_repo(self):
        """Validate that this is an official clone and on master branch.

        Returns (is_valid, error_message, details_dict).
        """
        details = {'is_official_clone': False, 'valid_branch': False, 'branch': ''}

        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=self.repo_path,
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, 'No origin remote found. Only clones from the official ECC-BFMC/Brain repository can be updated from here.', details

        origin_url = result.stdout.strip().lower()
        official_patterns = ['ecc-bfmc/brain.git', 'ecc-bfmc/brain']
        if not any(pat in origin_url for pat in official_patterns):
            return False, 'This repository was not cloned from the official ECC-BFMC/Brain repository. Only official clones can be updated from here.', details

        details['is_official_clone'] = True

        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=self.repo_path,
            capture_output=True, text=True, timeout=10
        )
        current_branch = branch_result.stdout.strip()
        details['branch'] = current_branch

        if current_branch not in ('main', 'master'):
            return False, f'Updates are only available on the master branch. You are currently on "{current_branch}".', details

        details['valid_branch'] = True
        return True, '', details

    def _ensure_official_remote(self):
        """Ensure the official BFMC remote is configured for updates."""
        result = subprocess.run(
            ['git', 'remote', 'get-url', self.OFFICIAL_REMOTE_NAME],
            cwd=self.repo_path,
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            subprocess.run(
                ['git', 'remote', 'add', self.OFFICIAL_REMOTE_NAME, self.OFFICIAL_REPO_URL],
                cwd=self.repo_path,
                capture_output=True, text=True, timeout=10
            )
        else:
            current_url = result.stdout.strip()
            if current_url != self.OFFICIAL_REPO_URL:
                subprocess.run(
                    ['git', 'remote', 'set-url', self.OFFICIAL_REMOTE_NAME, self.OFFICIAL_REPO_URL],
                    cwd=self.repo_path,
                    capture_output=True, text=True, timeout=10
                )

        return self.OFFICIAL_REMOTE_NAME

    def handle_check(self):
        """Check if there are updates available from the official BFMC repository."""
        try:
            is_valid, validation_msg, details = self._validate_repo()
            if not is_valid:
                return jsonify({
                    'success': True,
                    'update_available': False,
                    'is_official_clone': details['is_official_clone'],
                    'valid_branch': details['valid_branch'],
                    'branch': details.get('branch', ''),
                    'validation_error': validation_msg
                })

            update_remote = self._ensure_official_remote()

            fetch_result = subprocess.run(
                ['git', 'fetch', update_remote],
                cwd=self.repo_path,
                capture_output=True, text=True, timeout=30
            )

            if fetch_result.returncode != 0:
                return jsonify({'success': False, 'error': 'Failed to fetch from official repository'}), 500

            current_branch = details['branch']

            current_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True, text=True, timeout=10
            )
            current_commit = current_result.stdout.strip()
            current_commit_short = current_commit[:7] if current_commit else ''

            remote_branch = f'{update_remote}/master'
            check_result = subprocess.run(
                ['git', 'rev-parse', remote_branch],
                cwd=self.repo_path,
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
                cwd=self.repo_path,
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

    def handle_pull(self):
        """Pull the latest updates from the official BFMC repository."""
        try:
            is_valid, validation_msg, details = self._validate_repo()
            if not is_valid:
                return jsonify({'success': False, 'error': validation_msg}), 403

            update_remote = self._ensure_official_remote()
            remote_branch = 'master'

            stash_result = subprocess.run(
                ['git', 'stash'],
                cwd=self.repo_path,
                capture_output=True, text=True, timeout=10
            )
            had_stash = 'No local changes' not in stash_result.stdout

            fetch_result = subprocess.run(
                ['git', 'fetch', update_remote],
                cwd=self.repo_path,
                capture_output=True, text=True, timeout=30
            )

            if fetch_result.returncode != 0:
                if had_stash:
                    subprocess.run(
                        ['git', 'stash', 'pop'],
                        cwd=self.repo_path,
                        capture_output=True, text=True, timeout=10
                    )
                return jsonify({
                    'success': False,
                    'error': 'Failed to fetch from official repository'
                }), 500

            merge_result = subprocess.run(
                ['git', 'merge', f'{update_remote}/{remote_branch}', '--no-edit'],
                cwd=self.repo_path,
                capture_output=True, text=True, timeout=60
            )

            if merge_result.returncode != 0:
                subprocess.run(
                    ['git', 'merge', '--abort'],
                    cwd=self.repo_path,
                    capture_output=True, text=True, timeout=10
                )
                if had_stash:
                    subprocess.run(
                        ['git', 'stash', 'pop'],
                        cwd=self.repo_path,
                        capture_output=True, text=True, timeout=10
                    )
                return jsonify({
                    'success': False,
                    'error': 'Merge conflict detected. Please resolve manually or contact support.'
                }), 500

            if had_stash:
                pop_result = subprocess.run(
                    ['git', 'stash', 'pop'],
                    cwd=self.repo_path,
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
