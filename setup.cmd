:; @() { true; }
@ goto startbatch

# --- BASH CODE SECTION (Linux, macOS, and Windows under Git Bash) ---
set -e

# Detect operating system
OS_TYPE="linux"
if [[ "${OSTYPE:-}" == "msys" || "${OSTYPE:-}" == "cygwin" || "${OSTYPE:-}" == "win32" ]]; then
  OS_TYPE="windows"
fi
echo "OS detected: $OS_TYPE"

# --- Platform-specific dependencies ---
if [ "$OS_TYPE" == "windows" ]; then
  echo "Checking Windows prerequisites..."
  # 1. Verify python, node, and npm are installed
  if command -v python &> /dev/null; then
    PYTHON_CMD="python"
  elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
  else
    echo "Error: Python is not installed or not in PATH."
    exit 1
  fi

  if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "Error: Node.js and npm must be installed and in PATH."
    exit 1
  fi

  PYTHON_ACTIVATE=".venv/Scripts/activate"
  VENV_ARGS=()
else
  echo "Installing Linux system dependencies..."
  # --- APT base (Linux / Raspberry Pi) --------------------------------------
  sudo apt-get update
  sudo apt-get upgrade -y
  sudo apt-get install -y \
    python3-pip python3-dev build-essential pkg-config \
    libgl1 libglib2.0-0 libssl-dev libffi-dev libcap-dev \
    python3-libcamera python3-picamera2 xdg-utils curl ca-certificates

  # --- Node.js (Linux / Raspberry Pi) ---------------------------------------
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs

  PYTHON_CMD="python3"
  PYTHON_ACTIVATE=".venv/bin/activate"
  VENV_ARGS=(--system-site-packages)
fi

# --- Repository ownership (Linux / Raspberry Pi) -----------------------------
if [ "$OS_TYPE" != "windows" ] && [ -d ".git" ]; then
  REPO_UID="$(id -u)"
  REPO_GID="$(id -g)"
  OWNERSHIP_PATHS=(.git)
  [ -e "src/data" ] && OWNERSHIP_PATHS+=(src/data)
  [ -e "runtime" ] && OWNERSHIP_PATHS+=(runtime)

  if [ -n "$(find "${OWNERSHIP_PATHS[@]}" -not -user "$REPO_UID" -print -quit 2>/dev/null)" ]; then
    echo "Repairing repository ownership for dashboard updates..."
    sudo chown -R "$REPO_UID:$REPO_GID" "${OWNERSHIP_PATHS[@]}"
  fi
fi

# --- Git submodules (Cross-platform) ---
if [ -f ".gitmodules" ]; then
  if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
    echo "Initializing git submodules..."
    git submodule update --init --recursive
  else
    echo "Warning: .gitmodules exists, but git metadata is unavailable; skipping submodule setup."
  fi
fi

# --- Python Virtual Environment (Cross-platform) ---
if [ -f "$PYTHON_ACTIVATE" ]; then
  echo "Python virtual environment already exists, reusing it..."
else
  echo "Setting up Python virtual environment..."
  $PYTHON_CMD -m venv "${VENV_ARGS[@]}" .venv
fi

if [ "$OS_TYPE" != "windows" ] && [ -f ".venv/pyvenv.cfg" ]; then
  if grep -q "^include-system-site-packages =" .venv/pyvenv.cfg; then
    sed -i "s/^include-system-site-packages = .*/include-system-site-packages = true/" .venv/pyvenv.cfg
  else
    printf "\ninclude-system-site-packages = true\n" >> .venv/pyvenv.cfg
  fi
fi

source "$PYTHON_ACTIVATE"

if [ "$OS_TYPE" != "windows" ]; then
  echo "Removing pip-installed picamera2 so Raspberry Pi OS camera bindings are used..."
  pip uninstall -y picamera2 >/dev/null 2>&1 || true
fi

echo "Upgrading pip, setuptools, wheel..."
$PYTHON_CMD -m pip install --upgrade pip setuptools wheel

echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt

# --- Global Node Packages (Cross-platform) ---
echo "Installing global Node packages..."
if [ "$OS_TYPE" == "windows" ]; then
  npm install -g @angular/cli@20.1.4 || true
else
  sudo npm i -g npm@10.8.2 @angular/cli@20.1.4
fi

# --- Frontend deps/build (Cross-platform) ---
echo "Installing frontend dependencies..."
pushd src/dashboard/frontend >/dev/null

if [ -d node_modules ]; then
  echo "node_modules already exists, syncing dependencies..."
  npm install --legacy-peer-deps
elif [ -f package-lock.json ]; then
  npm ci --legacy-peer-deps
else
  npm install --legacy-peer-deps
fi

popd >/dev/null

echo "Setup complete."
exit 0

:startbatch
@echo off
rem --- WINDOWS BATCH SECTION ---
where bash >nul 2>nul
if %errorlevel% equ 0 (
    bash "%~dp0setup.cmd"
    exit /b
)

if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%~dp0setup.cmd"
    exit /b
)

rem --- Detect Git install path from the git command ---
for /f "delims=" %%G in ('where git 2^>nul') do (
    set "GIT_EXE=%%G"
    goto :found_git
)
goto :no_git

:found_git
rem git.exe is typically at <install>\cmd\git.exe; bash is at <install>\bin\bash.exe
for %%I in ("%GIT_EXE%") do set "GIT_DIR=%%~dpI"
set "GIT_BASH=%GIT_DIR%..\bin\bash.exe"
if exist "%GIT_BASH%" (
    "%GIT_BASH%" "%~dp0setup.cmd"
    exit /b
)

:no_git
echo Error: Git Bash was not found. Please ensure Git for Windows is installed and in PATH.
echo https://git-scm.com/
pause
exit /b 1
