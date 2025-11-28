#!/usr/bin/env bash
set -e

echo "=== Installing InfluxDB2 ==="

curl -sL https://repos.influxdata.com/influxdb.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/influxdb.gpg

echo "deb [signed-by=/usr/share/keyrings/influxdb.gpg] \
https://repos.influxdata.com/debian bullseye stable" \
  | sudo tee /etc/apt/sources.list.d/influxdb.list

sudo apt update
sudo apt install -y influxdb2
sudo systemctl enable influxdb
sudo systemctl start influxdb

echo "InfluxDB2 installed + started."