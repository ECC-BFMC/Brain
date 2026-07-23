"""Static integration checks for fallback service installation."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
WIFI_SERVICE = ROOT / "services" / "rpi-wifi-fallback"


def test_fallback_service_can_be_started_for_each_disconnect():
    service = (WIFI_SERVICE / "wifi-fallback.service").read_text(encoding="utf-8")

    assert "Type=oneshot" in service
    assert "RemainAfterExit=yes" not in service
    assert "systemd-tmpfiles-setup.service" in service


def test_dispatcher_triggers_non_blocking_reconciliation():
    dispatcher = (WIFI_SERVICE / "90-wifi-fallback").read_text(encoding="utf-8")

    assert '[[ "$IFACE_EVENT" == "$IFACE" && "$ACTION" == "down" ]]' in dispatcher
    assert '[[ "${CONNECTION_ID:-}" != "$CON_NAME" ]]' in dispatcher
    assert "systemctl --no-block start wifi-fallback.service" in dispatcher


def test_installer_deploys_dispatcher_helper_and_shared_lock():
    install = (WIFI_SERVICE / "install.sh").read_text(encoding="utf-8")
    tmpfiles = (
        WIFI_SERVICE / "rpi-wifi-fallback.conf"
    ).read_text(encoding="utf-8")
    fallback = (WIFI_SERVICE / "fallback.sh").read_text(encoding="utf-8")

    assert 'cp fallback.sh add-wifi.sh config.env "$DEST_DIR/"' in install
    assert '90-wifi-fallback "$DISPATCHER_PATH"' in install
    assert 'rpi-wifi-fallback.conf "$TMPFILES_PATH"' in install
    assert 'brain-monitor-wifi.conf "$BRAIN_DROPIN_PATH"' in install
    assert "systemd-tmpfiles --create" in install
    assert "/run/rpi-wifi-fallback/operation.lock" in tmpfiles
    assert "/run/rpi-wifi-fallback/operation.lock" in fallback


def test_wifi_installer_enforces_brain_service_sandbox():
    dropin = (
        WIFI_SERVICE / "brain-monitor-wifi.conf"
    ).read_text(encoding="utf-8")
    install = (WIFI_SERVICE / "install.sh").read_text(encoding="utf-8")

    assert "NoNewPrivileges=true" in dropin
    assert "SupplementaryGroups=brain-network" in dropin
    assert "groupadd --system brain-network" in install
    assert "usermod --append --groups brain-network pi" in install
    assert "systemctl try-restart brain-monitor.service" in install
