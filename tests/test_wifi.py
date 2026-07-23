"""Unit tests for the NetworkManager-backed Wi-Fi API handlers."""

from contextlib import nullcontext
from unittest.mock import MagicMock, call, patch

import pytest
from flask import Flask

from src.dashboard.components.wifi import (
    WifiCommandError,
    WifiManager,
    WifiPermissionError,
)


@pytest.fixture
def wifi(tmp_path):
    manager = WifiManager(str(tmp_path))
    manager.lock_file = str(tmp_path / "operation.lock")
    manager._require_permissions = MagicMock()
    return manager


@pytest.fixture(autouse=True)
def app_context():
    app = Flask(__name__)
    with app.app_context():
        yield


def body(response):
    resp = response[0] if isinstance(response, tuple) else response
    return resp.get_json()


def status(response):
    return response[1] if isinstance(response, tuple) else 200


def profile(
    name="HomeNet",
    connection_uuid="home-uuid",
    ssid=None,
    mode="infrastructure",
    active=False,
):
    return {
        "uuid": connection_uuid,
        "name": name,
        "ssid": ssid or name,
        "mode": mode,
        "active": active,
    }


def nmcli_result(returncode=0, stdout="", stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


def test_split_terse_line_unescapes_colons_and_backslashes():
    assert WifiManager._split_terse_line(
        r"uuid:Cafe\: Upstairs\\5G:802-11-wireless"
    ) == ["uuid", r"Cafe: Upstairs\5G", "802-11-wireless"]


def test_list_returns_uuid_active_state_and_filters_hotspots(wifi):
    saved = [
        profile(active=True),
        profile(name="Cafe", connection_uuid="cafe-uuid"),
        profile(
            name="rpi-hotspot",
            connection_uuid="hotspot-uuid",
            mode="ap",
            active=True,
        ),
    ]
    with patch.object(wifi, "_wifi_profiles", return_value=saved):
        response = wifi.handle_list()

    assert body(response)["networks"] == [
        {"uuid": "home-uuid", "name": "HomeNet", "active": True},
        {"uuid": "cafe-uuid", "name": "Cafe", "active": False},
    ]


def test_list_surfaces_nmcli_failure(wifi):
    with patch.object(
        wifi,
        "_wifi_profiles",
        side_effect=WifiCommandError("insufficient privileges"),
    ):
        response = wifi.handle_list()

    assert status(response) == 500
    assert "insufficient privileges" in body(response)["error"]


def test_nmcli_classifies_permission_denial(wifi):
    denied = nmcli_result(
        returncode=1,
        stderr="Connection deletion failed: Insufficient privileges",
    )
    with patch(
        "src.dashboard.components.wifi.subprocess.run",
        return_value=denied,
    ):
        with pytest.raises(WifiPermissionError):
            wifi._nmcli("connection", "delete", "uuid", "home-uuid")


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"ssid": "", "password": ""},
        {"ssid": "Net", "password": ""},
        {"ssid": "Net", "password": "short"},
    ],
)
def test_add_validates_request_and_wpa_password(wifi, payload):
    assert status(wifi.handle_add(payload)) == 400


def test_add_prepares_profile_before_returning_accepted(wifi):
    existing = profile(active=True)
    with (
        patch.object(wifi, "_wifi_profiles", return_value=[existing]),
        patch.object(
            wifi,
            "_create_candidate",
            return_value="candidate-uuid",
        ) as create_candidate,
        patch("src.dashboard.components.wifi.threading.Thread") as thread,
    ):
        response = wifi.handle_add({
            "ssid": " HomeNet ",
            "password": "  secret  ",
        })

    assert status(response) == 202
    payload = body(response)
    assert payload["success"] is True
    assert payload["operation_id"]
    create_candidate.assert_called_once()
    assert create_candidate.call_args.args[:2] == ("HomeNet", "  secret  ")
    thread.assert_called_once()
    assert thread.call_args.kwargs["daemon"] is True
    assert thread.call_args.args == ()
    worker_args = thread.call_args.kwargs["args"]
    assert worker_args[1:] == (
        "HomeNet",
        "candidate-uuid",
        ["home-uuid"],
        "home-uuid",
    )
    thread.return_value.start.assert_called_once_with()


def test_add_returns_real_preparation_error(wifi):
    with (
        patch.object(wifi, "_wifi_profiles", return_value=[]),
        patch.object(
            wifi,
            "_create_candidate",
            side_effect=WifiCommandError("Not authorized"),
        ),
        patch("src.dashboard.components.wifi.threading.Thread") as thread,
    ):
        response = wifi.handle_add({
            "ssid": "HomeNet",
            "password": "secret12",
        })

    assert status(response) == 500
    assert body(response)["error"] == "Not authorized"
    thread.assert_not_called()


def test_add_permission_denial_happens_before_profile_creation(wifi):
    wifi._require_permissions.side_effect = WifiPermissionError(
        "Polkit denied modify.system"
    )
    with patch.object(wifi, "_create_candidate") as create_candidate:
        response = wifi.handle_add({
            "ssid": "HomeNet",
            "password": "secret12",
        })

    assert status(response) == 403
    create_candidate.assert_not_called()


def test_add_rejects_concurrent_operation(wifi):
    first = wifi._begin_operation("add", "First")
    assert first

    response = wifi.handle_add({
        "ssid": "Second",
        "password": "secret12",
    })

    assert status(response) == 409


def test_activation_replaces_old_profile_only_after_success(wifi):
    def run_nmcli(*args, **_kwargs):
        return nmcli_result()

    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch.object(wifi, "_radio_lock", return_value=nullcontext()),
        patch.object(wifi, "_nmcli", side_effect=run_nmcli) as run,
        patch.object(wifi, "_stop_hotspot"),
        patch.object(wifi, "_hotspot_profile", return_value=None),
        patch.object(wifi, "_delete_profile") as delete_profile,
    ):
        operation_id = wifi._begin_operation("add", "HomeNet")
        wifi._activate_candidate(
            operation_id,
            "HomeNet",
            "candidate-uuid",
            ["old-uuid"],
            "old-uuid",
        )

    delete_profile.assert_called_once_with("old-uuid", ignore_missing=True)
    commands = [entry.args for entry in run.call_args_list]
    assert any(
        command[:6] == (
            "connection",
            "modify",
            "uuid",
            "candidate-uuid",
            "connection.id",
            "HomeNet",
        )
        for command in commands
    )
    assert wifi._operations[operation_id]["state"] == "connected"


def test_failed_activation_keeps_old_profile_and_restores_it(wifi):
    def run_nmcli(*args, **_kwargs):
        if "connection" in args and "up" in args:
            target_uuid = args[args.index("uuid") + 1]
            if target_uuid == "old-uuid":
                return nmcli_result()
            return nmcli_result(returncode=4, stderr="bad password")
        return nmcli_result()

    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch.object(wifi, "_radio_lock", return_value=nullcontext()),
        patch.object(wifi, "_nmcli", side_effect=run_nmcli),
        patch.object(wifi, "_stop_hotspot"),
        patch.object(wifi, "_delete_profile") as delete_profile,
        patch.object(wifi, "_start_fallback") as fallback,
    ):
        operation_id = wifi._begin_operation("add", "HomeNet")
        wifi._activate_candidate(
            operation_id,
            "HomeNet",
            "candidate-uuid",
            ["old-uuid"],
            "old-uuid",
        )

    delete_profile.assert_called_once_with(
        "candidate-uuid",
        ignore_missing=True,
    )
    fallback.assert_not_called()
    operation = wifi._operations[operation_id]
    assert operation["state"] == "failed"
    assert "previous Wi-Fi connection was restored" in operation["message"]


def test_failed_activation_starts_fallback_after_releasing_lock(wifi):
    events = []

    class RecordingLock:
        def __enter__(self):
            events.append("lock-enter")

        def __exit__(self, *_args):
            events.append("lock-exit")

    def run_nmcli(*args, **_kwargs):
        if "connection" in args and "up" in args:
            return nmcli_result(returncode=4, stderr="not found")
        return nmcli_result()

    def start_fallback():
        events.append("fallback")
        return True

    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch.object(wifi, "_radio_lock", return_value=RecordingLock()),
        patch.object(wifi, "_nmcli", side_effect=run_nmcli),
        patch.object(wifi, "_stop_hotspot"),
        patch.object(wifi, "_delete_profile"),
        patch.object(wifi, "_start_fallback", side_effect=start_fallback),
    ):
        operation_id = wifi._begin_operation("add", "HomeNet")
        wifi._activate_candidate(
            operation_id,
            "HomeNet",
            "candidate-uuid",
            [],
            None,
        )

    assert events == ["lock-enter", "lock-exit", "fallback"]
    assert wifi._operations[operation_id]["state"] == "failed"


def test_remove_inactive_profile_is_synchronous_and_uses_uuid(wifi):
    saved = profile()
    with (
        patch.object(wifi, "_wifi_profiles", return_value=[saved]),
        patch.object(wifi, "_delete_profile") as delete_profile,
    ):
        response = wifi.handle_remove("home-uuid")

    assert status(response) == 200
    assert body(response)["state"] == "completed"
    delete_profile.assert_called_once_with("home-uuid")


def test_remove_active_profile_returns_operation(wifi):
    saved = profile(active=True)
    with (
        patch.object(wifi, "_wifi_profiles", return_value=[saved]),
        patch("src.dashboard.components.wifi.threading.Thread") as thread,
    ):
        response = wifi.handle_remove("home-uuid")

    assert status(response) == 202
    assert body(response)["operation_id"]
    thread.assert_called_once_with(
        target=wifi._remove_active_connection,
        args=(body(response)["operation_id"], saved),
        daemon=True,
    )


def test_remove_active_permission_denial_does_not_disconnect(wifi):
    saved = profile(active=True)
    wifi._require_permissions.side_effect = WifiPermissionError(
        "Polkit denied network-control"
    )
    with (
        patch.object(wifi, "_wifi_profiles", return_value=[saved]),
        patch("src.dashboard.components.wifi.threading.Thread") as thread,
    ):
        response = wifi.handle_remove("home-uuid")

    assert status(response) == 403
    thread.assert_not_called()


def test_remove_active_profile_starts_fallback_after_delete(wifi):
    saved = profile(active=True)
    events = []

    class RecordingLock:
        def __enter__(self):
            events.append("lock-enter")

        def __exit__(self, *_args):
            events.append("lock-exit")

    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch.object(wifi, "_radio_lock", return_value=RecordingLock()),
        patch.object(wifi, "_nmcli", return_value=nmcli_result()),
        patch.object(
            wifi,
            "_delete_profile",
            side_effect=lambda *_args, **_kwargs: events.append("delete"),
        ),
        patch.object(
            wifi,
            "_start_fallback",
            side_effect=lambda: events.append("fallback") or True,
        ),
    ):
        operation_id = wifi._begin_operation("remove", "HomeNet")
        wifi._remove_active_connection(operation_id, saved)

    assert events == ["lock-enter", "delete", "lock-exit", "fallback"]
    assert wifi._operations[operation_id]["state"] == "completed"


def test_direct_fallback_does_not_wait_for_another_reconciler(wifi, tmp_path):
    fallback = tmp_path / "fallback.sh"
    fallback.write_text("#!/bin/bash\n", encoding="utf-8")

    with (
        patch("src.dashboard.components.wifi.os.path.isfile", return_value=True),
        patch("src.dashboard.components.wifi.subprocess.Popen") as popen,
    ):
        assert wifi._start_fallback() is True

    env = popen.call_args.kwargs["env"]
    assert env["LOCK_WAIT_SECONDS"] == "0"


def test_remove_failure_starts_fallback_when_restore_is_denied(wifi):
    saved = profile(active=True)

    def run_nmcli(*args, **_kwargs):
        if "connection" in args and "up" in args:
            raise WifiPermissionError("restore denied")
        return nmcli_result()

    with (
        patch("src.dashboard.components.wifi.time.sleep"),
        patch.object(wifi, "_radio_lock", return_value=nullcontext()),
        patch.object(wifi, "_nmcli", side_effect=run_nmcli),
        patch.object(
            wifi,
            "_delete_profile",
            side_effect=WifiPermissionError("delete denied"),
        ),
        patch.object(wifi, "_start_fallback", return_value=True) as fallback,
    ):
        operation_id = wifi._begin_operation("remove", "HomeNet")
        wifi._remove_active_connection(operation_id, saved)

    fallback.assert_called_once_with()
    operation = wifi._operations[operation_id]
    assert operation["state"] == "failed"
    assert "restoring the fallback hotspot" in operation["message"]


def test_remove_protects_hotspot_by_mode(wifi):
    hotspot = profile(
        name="CustomHotspot",
        connection_uuid="hotspot-uuid",
        mode="ap",
        active=True,
    )
    with patch.object(wifi, "_wifi_profiles", return_value=[hotspot]):
        response = wifi.handle_remove("hotspot-uuid")

    assert status(response) == 400


def test_operation_status_reports_terminal_result(wifi):
    operation_id = wifi._begin_operation("remove", "Cafe")
    wifi._update_operation(operation_id, "completed", "Removed")

    response = wifi.handle_operation(operation_id)

    assert body(response)["operation"]["state"] == "completed"
    assert body(response)["operation"]["message"] == "Removed"
