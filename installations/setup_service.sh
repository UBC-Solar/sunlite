echo "------- Installing systemd service (cellular-logger) -------"

SERVICE_SRC="installations/cellular-logger.service"
SERVICE_DST="/etc/systemd/system/cellular-logger.service"

# 1. Verify the service file exists
if [ ! -f "$SERVICE_SRC" ]; then
    echo "ERROR: $SERVICE_SRC not found. Cannot install service."
    exit 1
fi

# 2. Copy into systemd directory
echo "Copying service file to $SERVICE_DST ..."
sudo cp "$SERVICE_SRC" "$SERVICE_DST"

# 3. Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# 4. Enable service at boot
echo "Enabling cellular-logger service..."
sudo systemctl enable cellular-logger

# 5. Start or restart service immediately
echo "Starting cellular-logger service..."
sudo systemctl restart cellular-logger

# 6. Status message
echo "cellular-logger service installed, enabled, and running."
echo "View logs using: sudo journalctl -u cellular-logger -f"