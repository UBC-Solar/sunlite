#!/usr/bin/env bash
set -e

for f in "$(dirname "$0")"/*.sh; do
    chmod +x "$f" 2>/dev/null || true
done

# echo "------- Updating system -------"
# sudo apt-get update
# sudo apt-get install -y python3 python3-venv python3-pip git curl gpg

# echo "------- Installing Tailscale -------"
# if ! command -v tailscale >/dev/null 2>&1; then
#   curl -fsSL https://tailscale.com/install.sh | sh
#   sudo systemctl enable tailscaled
#   sudo systemctl start tailscaled
#   echo "You must run: sudo tailscale up (manually)"
# fi

echo "------- Setting up Python virtual environment -------"
./setup_python.sh

echo "------- Installing systemd service -------"
./scripts/setup_service.sh

echo "----------------------------------------------------------"
echo "INSTALL COMPLETE!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in values"
echo "2. Manually run: sudo tailscale up"
echo "3. Start the service: sudo systemctl start cellular-logger"
echo "----------------------------------------------------------"