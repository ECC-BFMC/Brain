"""Unit tests for the Brain update manager's pure logic.

UpdateManager applies codebase updates via git, but its URL handling, config
persistence, auth-error detection and dependency-change detection are pure and
security-relevant (the URL validator blocks transports that could run commands
or read local files). Those are tested here; the git/network paths are not.
"""

from types import SimpleNamespace

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
