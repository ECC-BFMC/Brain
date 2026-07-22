"""Regression checks for asynchronous Wi-Fi profile removal."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "services" / "rpi-wifi-fallback" / "remove-wifi.sh"


def bash_executable():
    bash = shutil.which("bash")
    if bash and "WindowsApps" not in bash:
        return bash

    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if git_bash.exists():
        return str(git_bash)

    pytest.skip("A usable Bash runtime is not installed")


def test_remove_wifi_script_has_valid_bash_syntax():
    result = subprocess.run(
        [bash_executable(), "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_removal_is_detached_before_active_connection_is_deleted():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "--setenv=REMOVEWIFI_DETACHED=1" in script
    assert script.index("sleep 2") < script.index('nmcli connection delete "$TARGET_NAME"')
    assert "if (( was_active )); then" in script
    assert '/bin/bash "$fallback_script" up' in script
