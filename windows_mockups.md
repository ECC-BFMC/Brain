# Windows Compatibility Mockups Needed

This document outlines the features and components in the BFMC Brain project that require mockups or cross-platform adaptations to run properly on Windows. Currently, these features depend on Linux-specific commands, device paths, or hardware APIs.

---

## 1. Camera Thread & Stream (`picamera2`)
* **Location:** `src/hardware/camera/threads/threadCamera.py`
* **Dependency:** The `picamera2` library, which controls the Raspberry Pi camera module via `libcamera`.
* **Issue on Windows:** Cannot be installed or imported because the underlying hardware and C/C++ libraries are missing on Windows.
* **Proposed Mockup Strategy:**
  - Introduce a try-except fallback block for the `picamera2` import.
  - Implement a mock class `Picamera2` that mimics the real library's interface:
    - `global_camera_info()`: Return a dummy camera descriptor list.
    - `create_preview_configuration()`, `configure()`, `start()`, `stop()`, `set_controls()`: Implement as no-ops.
    - `capture_array("main")`: Return a mock RGB888 numpy array (e.g., size $2048 \times 1080 \times 3$) containing a dynamic test pattern (gradient background, moving geometric shapes, or timestamp text).
    - `capture_array("lores")`: Return a mock YUV I420 numpy array (e.g., size $405 \times 512$) constructed by converting a low-res BGR test frame using `cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)`.

---

## 2. WiFi Network Management (`nmcli`)
* **Location:** `src/dashboard/components/wifi.py`
* **Dependency:** System subprocesses invoking `nmcli` (NetworkManager CLI) and local bash scripts (`add-wifi.sh` and `fallback.sh`).
* **Issue on Windows:** `nmcli` is not available, and shell scripts will fail to execute or locate hardware interfaces.
* **Proposed Mockup Strategy:**
  - Detect the Windows environment using `sys.platform == "win32"`.
  - Bypass `subprocess` invocations inside the `WifiManager` handlers.
  - Mock handlers:
    - `handle_list()`: Return a hardcoded list of dummy WiFi connections (e.g., `[{"name": "Mock WiFi 1"}, {"name": "Mock WiFi 2"}]`).
    - `handle_add()`: Return a successful response simulating the connection attempt.
    - `handle_remove()`: Return a success response simulating hotspot activation.

---

## 3. Nucleo Firmware Flashing
* **Location:** `src/dashboard/components/firmware.py`
* **Dependency:** Mount point scanning pattern (`/media/pi/NOD_F401RE*`) and the Linux `sync` shell command.
* **Issue on Windows:** Mount directories use drive letters (e.g. `E:\`, `F:\`), and the `sync` shell command is unavailable.
* **Proposed Mockup/Adaptation Strategy:**
  - Adapt `_find_nucleo_mount` on Windows to check drive letters `A-Z` for standard Nucleo USB files (like `MBED.HTM` or `DETAILS.TXT`).
  - If no board is physically plugged in, mock the detection and flashing by simulating copy operations.
  - Wrap the `sync` subprocess invocation so that it is skipped on Windows:
    ```python
    if sys.platform != 'win32':
        subprocess.run(['sync'], timeout=10)
    ```
