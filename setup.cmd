:; @() { true; }
@ goto startbatch

# --- BASH CODE SECTION (Linux, macOS, and Windows under Git Bash) ---
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
else
  echo "Installing Linux system dependencies..."
  # --- APT base (Linux / Raspberry Pi) --------------------------------------
  sudo apt-get update
  sudo apt-get upgrade -y
  sudo apt-get install -y \
    python3-pip python3-dev build-essential pkg-config \
    libgl1 libglib2.0-0 libssl-dev libffi-dev \
    python3-libcamera xdg-utils curl ca-certificates

  # --- Node.js (Linux / Raspberry Pi) ---------------------------------------
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs

  PYTHON_CMD="python3"
  PYTHON_ACTIVATE=".venv/bin/activate"
fi

# --- Python Virtual Environment (Cross-platform) ---
echo "Setting up Python virtual environment..."
$PYTHON_CMD -m venv .venv
source "$PYTHON_ACTIVATE"

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

if [ -f package-lock.json ]; then
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

echo Error: Git Bash was not found in PATH or at "C:\Program Files\Git\bin\bash.exe".
echo Please install Git for Windows (https://git-scm.com/) and try again.
pause
exit /b 1
