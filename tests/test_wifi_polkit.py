"""Regression tests for dashboard NetworkManager authorization."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
WIFI_SERVICE = ROOT / "services" / "rpi-wifi-fallback"
RULE_NAME = "49-brain-networkmanager.rules"


def test_polkit_rule_is_scoped_to_brain_service_and_required_actions():
    rule = (WIFI_SERVICE / RULE_NAME).read_text(encoding="utf-8")

    assert 'subject.user !== "pi"' in rule
    assert 'subject.system_unit !== "brain-monitor.service"' in rule
    assert "subject.no_new_privileges !== true" in rule
    assert "subject.local" not in rule
    assert 'action.id.indexOf("org.freedesktop.NetworkManager.")' not in rule

    required_actions = {
        "org.freedesktop.NetworkManager.enable-disable-wifi",
        "org.freedesktop.NetworkManager.network-control",
        "org.freedesktop.NetworkManager.settings.modify.own",
        "org.freedesktop.NetworkManager.settings.modify.system",
        "org.freedesktop.NetworkManager.wifi.scan",
    }
    assert all(action in rule for action in required_actions)


def test_installer_and_uninstaller_manage_polkit_rule():
    install = (WIFI_SERVICE / "install.sh").read_text(encoding="utf-8")
    uninstall = (WIFI_SERVICE / "uninstall.sh").read_text(encoding="utf-8")

    assert RULE_NAME in install
    assert 'install -D -o root -g root -m 0644' in install
    assert RULE_NAME in uninstall
    assert 'rm -f "$POLKIT_RULE_PATH"' in uninstall


def test_brain_service_enables_no_new_privileges():
    service = (
        ROOT / "services" / "brain-autostart" / "brain-monitor.service"
    ).read_text(encoding="utf-8")

    assert "User=pi" in service
    assert "NoNewPrivileges=true" in service
