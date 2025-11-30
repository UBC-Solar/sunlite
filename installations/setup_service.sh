#!/usr/bin/env bash
set -e

# Absolute paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${PROJECT_ROOT}/installations"

SERVICE_SRC="${INSTALL_DIR}/cellular-logger.service"
SERVICE_DST="/etc/systemd/system/cellular-logger.service"

echo "------- Installing systemd service (cellular-logger) -------"

if [ ! -f "$SERVICE_SRC" ]; then
  echo "ERROR: ${SERVICE_SRC} not found. Cannot install service."
  exit 1
fi

echo "Copying service file to ${SERVICE_DST}..."
sudo cp "$SERVICE_SRC" "$SERVICE_DST"

echo "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable cellular-logger.service
sudo systemctl restart cellular-logger.service

echo "Systemd service installed and started."
