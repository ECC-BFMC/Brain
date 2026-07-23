"""Unit tests for the Brain update manager's pure logic.

UpdateManager applies codebase updates via git, but its URL handling, config
persistence, auth-error detection and dependency-change detection are pure and
security-relevant (the URL validator blocks transports that could run commands
or read local files). Those are tested here; the git/network paths are not.
"""

from types import SimpleNamespace
import subprocess

import pytest
from flask import Flask

from src.dashboard.components.updates import UpdateManager


@pytest.fixture
def updates(tmp_path):
    return UpdateManager(str(tmp_path))


@pytest.fixture
def app_context():
    app = Flask(__name__)
    with app.app_context():
        yield


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def git_update_repo(tmp_path):
    """A car clone at v1 plus an origin containing a fast-forward v2."""
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    car = tmp_path / "car"

    _git(tmp_path, "init", "--bare", str(remote))
    source.mkdir()
    _git(source, "init")
    _git(source, "config", "user.name", "Update Test")
    _git(source, "config", "user.email", "update-test@example.invalid")
    (source / "app.txt").write_text("v1\n", encoding="utf-8")
    _git(source, "add", "app.txt")
    _git(source, "commit", "-m", "v1")
    _git(source, "branch", "-M", "main")
    _git(source, "remote", "add", "origin", str(remote))
    _git(source, "push", "-u", "origin", "main")
    _git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

    _git(tmp_path, "clone", "--branch", "main", str(remote), str(car))
    previous_head = _git(car, "rev-parse", "HEAD")

    (source / "app.txt").write_text("v2\n", encoding="utf-8")
    _git(source, "add", "app.txt")
    _git(source, "commit", "-m", "v2")
    _git(source, "push", "origin", "main")
    target_head = _git(source, "rev-parse", "HEAD")

    manager = UpdateManager(str(car))
    manager._save_config({
        "remote_name": UpdateManager.DEFAULT_REMOTE_NAME,
        "url": "",
        "branch": "main",
    })
    return manager, car, previous_head, target_head


# --------------------------------------------------------------------------- #
# _to_https_url
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,expected", [
    ("git@github.com:o/r.git", "https://github.com/o/r.git"),
    ("ssh://git@github.com/o/r.git", "https://github.com/o/r.git"),
    ("https://github.com/o/r", "https://github.com/o/r"),  # unchanged
    ("", ""),
])
def test_to_https_url(updates, url, expected):
    assert updates._to_https_url(url) == expected


# --------------------------------------------------------------------------- #
# _validate_repo_url  (security guard)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url", [
    "https://github.com/o/r",
    "ssh://git@github.com/o/r.git",
    "git@github.com:o/r.git",
])
def test_validate_repo_url_accepts_supported_transports(updates, url):
    ok, _ = updates._validate_repo_url(url)
    assert ok is True


@pytest.mark.parametrize("url", [
    "",
    "ext::sh -c whoami",
    "file:///etc/passwd",
    "-oProxyCommand=evil",
    "ftp://example.com/repo",
])
def test_validate_repo_url_rejects_dangerous_or_unsupported(updates, url):
    ok, err = updates._validate_repo_url(url)
    assert ok is False
    assert err


# --------------------------------------------------------------------------- #
# _parse_github_repo / _is_auth_error / _deps_changed
# --------------------------------------------------------------------------- #
def test_parse_github_repo_returns_owner_repo_tuple(updates):
    assert updates._parse_github_repo("https://github.com/owner/repo.git") == ("owner", "repo")


def test_parse_github_repo_rejects_non_github(updates):
    assert updates._parse_github_repo("https://gitlab.com/o/r") is None


@pytest.mark.parametrize("text,expected", [
    ("fatal: Authentication failed for 'x'", True),
    ("remote: Repository not found", True),
    ("Could not resolve host: github.com", False),
    ("", False),
])
def test_is_auth_error(updates, text, expected):
    assert updates._is_auth_error(text) is expected


def test_fetch_failure_response_explains_submodule_permission_error(updates, app_context):
    fetch = SimpleNamespace(
        stderr="error: cannot open 'FETCH_HEAD': Permission denied\nErrors during submodule fetch:\nsrc/data",
        stdout="",
    )

    response, status = updates._fetch_failure_response(fetch)
    payload = response.get_json()

    assert status == 500
    assert "sudo chown -R" in payload["error"]
    assert "submodules" in payload["error"]


@pytest.mark.parametrize("files,expected", [
    (["a/requirements.txt"], True),
    (["src/dashboard/frontend/package.json"], True),
    (["src/dashboard/frontend/package-lock.json"], True),
    (["main.py", "README.md"], False),
    ([], False),
])
def test_deps_changed(updates, files, expected):
    assert updates._deps_changed(files) is expected


def test_success_message_mentions_deps_only_when_changed(updates):
    assert "Dependencies changed" in updates._success_message(True)
    assert "Dependencies changed" not in updates._success_message(False)
    assert "discarded" in updates._success_message(False, forced=True)


# --------------------------------------------------------------------------- #
# config persistence roundtrip
# --------------------------------------------------------------------------- #
def test_config_roundtrip(updates):
    cfg = {"remote_name": "bfmc-upstream", "url": "https://github.com/me/fork", "branch": "dev"}
    updates._save_config(cfg)
    assert updates._load_config() == cfg


def test_load_config_defaults_when_absent(updates):
    cfg = updates._load_config()
    assert cfg == {"remote_name": UpdateManager.DEFAULT_REMOTE_NAME, "url": "", "branch": ""}


# --------------------------------------------------------------------------- #
# branch/source validation (Flask context; no git needed for the reject paths)
# --------------------------------------------------------------------------- #
def test_set_branch_rejects_flags_and_whitespace(updates, app_context):
    _resp, code = updates.handle_set_branch("-x")
    assert code == 400
    _resp, code = updates.handle_set_branch("has space")
    assert code == 400


def test_set_source_rejects_invalid_url(updates, app_context):
    _resp, code = updates.handle_set_source("file:///etc/passwd")
    assert code == 400


# --------------------------------------------------------------------------- #
# transactional update safety
# --------------------------------------------------------------------------- #
def test_fetch_enables_object_verification(updates, monkeypatch):
    captured = {}

    def fake_git(*args, **kwargs):
        captured["args"] = args
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(updates, "_git", fake_git)

    updates._fetch_verified("origin")

    assert captured["args"] == (
        "-c", "core.fsync=all",
        "-c", "core.fsyncMethod=fsync",
        "-c", "fetch.fsckObjects=true",
        "-c", "transfer.fsckObjects=true",
        "fetch", "origin", "--recurse-submodules",
    )
    assert captured["timeout"] == 300


def test_update_guard_rejects_overlapping_operation(updates, app_context):
    with updates._update_guard() as acquired:
        assert acquired is True
        response, status = updates.handle_pull()

    assert status == 409
    assert response.get_json()["update_in_progress"] is True


def test_verified_update_is_staged_then_applied(git_update_repo, app_context):
    manager, car, _previous_head, target_head = git_update_repo

    response = manager.handle_pull()
    payload = response.get_json()

    assert payload["success"] is True
    assert _git(car, "rev-parse", "HEAD") == target_head
    assert (car / "app.txt").read_text(encoding="utf-8") == "v2\n"


def test_staging_failure_leaves_live_checkout_untouched(
    git_update_repo, app_context, monkeypatch
):
    manager, car, previous_head, _target_head = git_update_repo
    monkeypatch.setattr(
        manager,
        "_validate_staged_checkout",
        lambda _commit, _files: (False, "simulated build failure"),
    )

    response, status = manager.handle_pull()
    payload = response.get_json()

    assert status == 422
    assert payload["verification_failed"] is True
    assert _git(car, "rev-parse", "HEAD") == previous_head
    assert (car / "app.txt").read_text(encoding="utf-8") == "v1\n"


def test_dirty_tracked_file_is_blocked_before_update(
    git_update_repo, app_context
):
    manager, car, previous_head, _target_head = git_update_repo
    (car / "app.txt").write_text("local edit\n", encoding="utf-8")

    response, status = manager.handle_pull()
    payload = response.get_json()

    assert status == 409
    assert payload["conflict"]["files"] == ["app.txt"]
    assert _git(car, "rev-parse", "HEAD") == previous_head
    assert (car / "app.txt").read_text(encoding="utf-8") == "local edit\n"


def test_failed_live_verification_rolls_back(
    git_update_repo, app_context, monkeypatch
):
    manager, car, previous_head, _target_head = git_update_repo
    monkeypatch.setattr(
        manager,
        "_verify_live_checkout",
        lambda _commit, _files: (False, "simulated live mismatch"),
    )

    response, status = manager.handle_pull()
    payload = response.get_json()

    assert status == 500
    assert payload["rolled_back"] is True
    assert _git(car, "rev-parse", "HEAD") == previous_head
    assert (car / "app.txt").read_text(encoding="utf-8") == "v1\n"


def test_force_update_discards_diverged_local_commit(
    git_update_repo, app_context
):
    manager, car, _previous_head, target_head = git_update_repo
    _git(car, "config", "user.name", "Car Test")
    _git(car, "config", "user.email", "car-test@example.invalid")
    (car / "app.txt").write_text("local branch\n", encoding="utf-8")
    _git(car, "add", "app.txt")
    _git(car, "commit", "-m", "local divergence")

    response = manager.handle_force_pull()
    payload = response.get_json()

    assert payload["success"] is True
    assert _git(car, "rev-parse", "HEAD") == target_head
    assert (car / "app.txt").read_text(encoding="utf-8") == "v2\n"


def test_corrupt_current_commit_is_rejected_before_fetch(
    git_update_repo, app_context, monkeypatch
):
    manager, car, previous_head, _target_head = git_update_repo
    monkeypatch.setattr(
        manager,
        "_verify_commit",
        lambda _commit: (False, "simulated corrupt object"),
    )

    response, status = manager.handle_pull()
    payload = response.get_json()

    assert status == 500
    assert payload["repository_corrupt"] is True
    assert _git(car, "rev-parse", "HEAD") == previous_head
