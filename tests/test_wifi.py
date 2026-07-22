"""Unit tests for the WiFi management API handlers.

WifiManager backs the /api/wifi routes. Its logic is input validation, the
protected-connection guard, and parsing nmcli output. The actual nmcli/script
calls are mocked; only the decision logic and HTTP status codes are asserted.
Responses are built with flask.jsonify, so an app context is active.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from src.dashboard.components.wifi import WifiManager


@pytest.fixture
def wifi(tmp_path):
    return WifiManager(str(tmp_path))


@pytest.fixture(autouse=True)
def app_context():
    app = Flask(__name__)
    with app.app_context():
        yield


def body(response):
    """Extract the JSON dict from a handler's (Response, status) or Response."""
    resp = response[0] if isinstance(response, tuple) else response
    return resp.get_json()


def status(response):
    return response[1] if isinstance(response, tuple) else 200


# --------------------------------------------------------------------------- #
# handle_add — validation
# --------------------------------------------------------------------------- #
def test_add_requires_ssid_and_password(wifi):
    assert status(wifi.handle_add({"ssid": "", "password": ""})) == 400
    assert status(wifi.handle_add({"ssid": "Net", "password": ""})) == 400


def test_add_fails_when_script_missing(wifi):
    # tmp repo has no services/rpi-wifi-fallback/add-wifi.sh
    resp = wifi.handle_add({"ssid": "Net", "password": "secret"})
    assert status(resp) == 500
    assert body(resp)["success"] is False


def test_add_launches_script_when_present(wifi, tmp_path):
    script = tmp_path / "services" / "rpi-wifi-fallback" / "add-wifi.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/sh\n")

    with patch("src.dashboard.components.wifi.subprocess.Popen") as popen:
        resp = wifi.handle_add({"ssid": "Net", "password": "secret"})

    assert body(resp)["success"] is True
    popen.assert_called_once()
    # The ssid/password are passed through to the script.
    args = popen.call_args[0][0]
    assert args[2] == "Net" and args[3] == "secret"


# --------------------------------------------------------------------------- #
# handle_remove — protected connections
# --------------------------------------------------------------------------- #
def test_remove_requires_name(wifi):
    assert status(wifi.handle_remove("")) == 400


@pytest.mark.parametrize("protected", ["rpi-hotspot", "preconfigured"])
def test_remove_rejects_protected_connections(wifi, protected):
    resp = wifi.handle_remove(protected)
    assert status(resp) == 400
    assert "Cannot remove" in body(resp)["error"]


def test_remove_schedules_background_worker(wifi):
    with patch("src.dashboard.components.wifi.threading.Thread") as thread:
        resp = wifi.handle_remove("HomeNet")

    assert body(resp)["success"] is True
    thread.assert_called_once_with(
        target=wifi._remove_connection,
        args=("HomeNet",),
        daemon=True,
    )
    thread.return_value.start.assert_called_once_with()


def test_remove_worker_uses_nmcli_without_sudo(wifi, tmp_path):
    fallback = tmp_path / "services" / "rpi-wifi-fallback" / "fallback.sh"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("#!/bin/bash\n")

    active = MagicMock(stdout="HomeNet\n", returncode=0)
    deleted = MagicMock(stdout="", stderr="", returncode=0)
    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch(
            "src.dashboard.components.wifi.subprocess.run",
            side_effect=[active, deleted],
        ) as run,
        patch("src.dashboard.components.wifi.subprocess.Popen") as popen,
    ):
        wifi._remove_connection("HomeNet")

    assert run.call_args_list[1].args[0] == [
        "nmcli", "connection", "delete", "HomeNet"
    ]
    popen.assert_called_once()
    assert popen.call_args.args[0] == ["/bin/bash", str(fallback), "up"]


def test_remove_worker_leaves_network_unchanged_for_inactive_profile(wifi):
    active = MagicMock(stdout="OtherNet\n", returncode=0)
    deleted = MagicMock(stdout="", stderr="", returncode=0)
    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch(
            "src.dashboard.components.wifi.subprocess.run",
            side_effect=[active, deleted],
        ),
        patch("src.dashboard.components.wifi.subprocess.Popen") as popen,
    ):
        wifi._remove_connection("HomeNet")

    popen.assert_not_called()


# --------------------------------------------------------------------------- #
# handle_list — nmcli parsing
# --------------------------------------------------------------------------- #
def test_list_filters_non_wifi_and_protected(wifi):
    nmcli_out = (
        "HomeNet:802-11-wireless\n"
        "eth0:802-3-ethernet\n"
        "rpi-hotspot:802-11-wireless\n"
        "Cafe:802-11-wireless\n"
    )
    with patch("src.dashboard.components.wifi.subprocess.run") as run:
        run.return_value = MagicMock(stdout=nmcli_out)
        resp = wifi.handle_list()

    names = {n["name"] for n in body(resp)["networks"]}
    assert names == {"HomeNet", "Cafe"}  # ethernet + protected filtered out
