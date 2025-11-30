#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install python-dotenv influxdb-client pyserial cantools