"""Unit tests for the hardware-free logic in the firmware manager.

FirmwareManager talks to GitHub and the Nucleo board, but its URL parsing,
config persistence, and local-path validation are pure and security-relevant
(the path validation is what stops a crafted filename escaping the firmware
folder). Those are tested here; the network/flash paths are not.
"""

import pytest
from flask import Flask

from src.dashboard.components.firmware import FirmwareManager


@pytest.fixture
def manager(tmp_path):
    return FirmwareManager(str(tmp_path))


@pytest.fixture
def app_context():
    """The handle_* methods build responses with flask.jsonify, which needs an
    application context to be active."""
    app = Flask(__name__)
    with app.app_context():
        yield


# --------------------------------------------------------------------------- #
# _parse_github_repo
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,expected", [
    ("git@github.com:owner/repo.git", "owner/repo"),
    ("git@github.com:owner/repo", "owner/repo"),
    ("https://github.com/owner/repo", "owner/repo"),
    ("https://github.com/owner/repo.git", "owner/repo"),
    ("https://www.github.com/owner/repo", "owner/repo"),
    ("ssh://git@github.com/owner/repo.git", "owner/repo"),
    ("https://github.com/owner/repo/tree/main", "owner/repo"),
])
def test_parse_github_repo_accepts_github_urls(manager, url, expected):
    assert manager._parse_github_repo(url) == expected


@pytest.mark.parametrize("url", [
    "",
    None,
    "not a url",
    "https://gitlab.com/owner/repo",       # wrong host
    "ssh://git@gitlab.com/owner/repo.git",  # wrong host
    "https://github.com/only-owner",        # missing repo
])
def test_parse_github_repo_rejects_non_github(manager, url):
    assert manager._parse_github_repo(url) is None


# --------------------------------------------------------------------------- #
# _resolve_repo / _resolve_file_path
# --------------------------------------------------------------------------- #
def test_resolve_repo_uses_configured_url(manager):
    assert manager._resolve_repo({"url": "https://github.com/me/fw"}) == "me/fw"


def test_resolve_repo_falls_back_to_default(manager):
    assert manager._resolve_repo({"url": ""}) == FirmwareManager.FIRMWARE_REPO
    assert manager._resolve_repo({"url": "garbage"}) == FirmwareManager.FIRMWARE_REPO


def test_resolve_file_path_default_and_override(manager):
    assert manager._resolve_file_path({}) == FirmwareManager.FIRMWARE_FILE_PATH
    assert manager._resolve_file_path({"file_path": "build/x.bin"}) == "build/x.bin"


# --------------------------------------------------------------------------- #
# config persistence roundtrip
# --------------------------------------------------------------------------- #
def test_config_save_load_roundtrip(manager):
    cfg = {"url": "https://github.com/me/fw", "branch": "dev", "file_path": "out/robot.bin"}
    manager._save_config(cfg)
    loaded = manager._load_config()
    assert loaded == cfg


def test_load_config_defaults_when_absent(manager):
    assert manager._load_config() == {"url": "", "branch": "", "file_path": ""}


# --------------------------------------------------------------------------- #
# _resolve_local_firmware_path  (path-traversal guard)
# --------------------------------------------------------------------------- #
def test_resolve_local_firmware_path_accepts_plain_bin(manager, tmp_path):
    fw_path, name = manager._resolve_local_firmware_path("robot_car.bin")
    assert name == "robot_car.bin"
    assert fw_path.endswith("robot_car.bin")
    # Must stay inside the firmware folder.
    assert "runtime" in fw_path and "firmware" in fw_path


@pytest.mark.parametrize("bad", [
    "",
    "no_extension",
    "firmware.txt",
    "../secret.bin",
    "sub/dir/robot.bin",
])
def test_resolve_local_firmware_path_rejects_bad_names(manager, bad):
    with pytest.raises(ValueError):
        manager._resolve_local_firmware_path(bad)


# --------------------------------------------------------------------------- #
# set_source URL validation (no network: invalid URL returns before any I/O)
# --------------------------------------------------------------------------- #
def test_handle_set_file_rejects_non_bin(manager, app_context):
    _resp, status = manager.handle_set_file("firmware.hex")
    assert status == 400


def test_handle_set_file_rejects_traversal(manager, app_context):
    _resp, status = manager.handle_set_file("../../etc/passwd.bin")
    assert status == 400
