#!/usr/bin/env bash
set -euo pipefail

# --- APT base ---------------------------------------------------------------
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y \
  python3-pip python3-dev build-essential pkg-config \
  libgl1 libglib2.0-0 libssl-dev libffi-dev \
  python3-libcamera xdg-utils curl ca-certificates

# --- Enable global pip installs --------------------------------------------
sudo pip3 config --global set global.break-system-packages true
sudo pip3 config --global set global.timeout 60
sudo pip3 config --global set global.no-cache-dir true
sudo pip3 config --global set global.prefer-binary true

# --- Node.js (system-wide via NodeSource; simpler than nvm for boot services)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm i -g npm@10.8.2 @angular/cli@20.1.4

# --- Python deps (GLOBAL) ---------------------------------------------------
sudo pip3 install -r requirements.txt

# --- Frontend deps/build ----------------------------------------------------
pushd src/dashboard/frontend >/dev/null

if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

popd >/dev/null

echo "Install complete."
