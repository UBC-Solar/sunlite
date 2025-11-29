#!/usr/bin/env bash
set -e

curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable tailscaled
sudo systemctl start tailscaled

echo ">>> Run 'sudo tailscale up' manually to authenticate."