# Sunlite RPi gRPC Cellular Client

This repository contains the **Raspberry Pi client** for Sunlite's cellular telemetry pipeline.

The Pi reads 24-byte CAN frames from the TEL board via UART, converts them to protobuf messages, batches them, and streams them over gRPC to the `cellular_parser` on the bay computer.

**UART → protobuf → batch → gRPC stream**

**Note:** The Pi does NOT parse CAN frames. It only forwards raw data. All parsing (DBC decoding, InfluxDB writing) happens on the bay computer.


## Architecture
```
┌─────────────┐        UART         ┌──────────────────────────┐
│  TEL Board  │ ───────────────────> │  Raspberry Pi (sunlite)  │
│             │   (24-byte frames)   │  100.117.111.10          │
└─────────────┘                      │                          │
                                     │  rpi_cellular.py         │
                                     │  - Read UART             │
                                     │  - Convert to protobuf   │
                                     │  - Batch                 │
                                     └────────────┬─────────────┘
                                                  │
                                                  │ gRPC stream
                                                  │ Cellular Hotspot
                                                  │
                                                  ▼
                                     ┌─────────────────────────────┐
                                     │   Bay Computer              │
                                     │   100.120.214.69:50051      │
                                     │                             │
                                     │  cellular_parser (Docker)   │
                                     │  - Parse CAN (DBC)          │
                                     │  - Write to InfluxDB        │
                                     └─────────────────────────────┘
```


## Repository Structure
```text
sunlite/
├── rpi_cellular.py         # Main client script
├── serial_input.py         # Debug: view raw UART frames
├── test_send.py            # Debug: send test frame to server
├── .env                    # Runtime configuration
├── .env.example            # Example configuration
├── requirements.txt        # Python dependencies
└── tools/
    └── proto/
        ├── canlink.proto
        ├── canlink_pb2.py
        └── canlink_pb2_grpc.py
```


## Prerequisites

### Hardware
- Raspberry Pi 4B with Raspberry Pi OS (64-bit, Bookworm)
- USB-UART adapter (e.g., FTDI C232HM-DDHSL-0)
- LTE/5G cellular hotspot
- TEL board connected via UART

### Software
- Python 3.10+
- Network connectivity to bay computer (`100.120.214.69:50051`)
- `cellular_parser` Docker container running on bay computer


## Installation

### 1. Clone Repository
```bash
cd ~
git clone https://github.com/UBC-Solar/sunlite.git
cd sunlite
```

### 2. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
nano .env
```

Example `.env`:
```bash
# UART configuration
TEL_UART_PORT=/dev/serial/by-id/usb-FTDI_C232HM-DDHSL-0_FT1K72V9-if00-port0
TEL_UART_BAUD=230400

# gRPC server
INGEST_SERVER=100.120.214.69:50051

# Batching
BATCH_SIZE=200
BATCH_MAX_MS=50

# Compression
GRPC_COMP=gzip
```

### 5. Set UART Permissions
```bash
sudo usermod -aG dialout sunlite
```

Log out and back in for changes to take effect.


## Configuration Variables

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `TEL_UART_PORT` | UART device path | `/dev/ttyUSB0` | Use `/dev/serial/by-id/...` for stable path |
| `TEL_UART_BAUD` | Baud rate | `230400` | Must match TEL board |
| `INGEST_SERVER` | gRPC endpoint | `100.120.214.69:50051` | Bay computer parser |
| `BATCH_SIZE` | Frames per batch | `200` | Tune for latency/throughput |
| `BATCH_MAX_MS` | Max batch time (ms) | `50` | Flush interval |
| `GRPC_COMP` | Compression mode | `gzip` | Options: `gzip`, `zstd`, `none` |


## Running the Client

### Step 1: Start Bay Computer Parser (Required)
```bash
ssh electrical@100.120.214.69
# password: elec2024

cd /home/electrical/sunlink
source environment/bin/activate

docker compose down
docker compose up -d
```

### Step 2: Start RPi Client
```bash
ssh sunlite@100.117.111.10
# password: solarisbest123

cd /home/tonychen/Mridul_gRPC
source .venv/bin/activate

set -a
source .env
set +a

./rpi_cellular.py
```

Expected output:
```
[RPi] UART open on /dev/ttyUSB0@230400, streaming to 100.120.214.69:50051
[RPi] stream closed, server ack: 773661 frames
```


## How It Works

### UART Frame Format (24 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0-7    | 8    | timestamp | double as uint64 (big-endian) |
| 8      | 1    | delimiter | `'#'` |
| 9-12   | 4    | can_id | uint32 (bit-reversed by TEL) |
| 13-20  | 8    | data | CAN data bytes |
| 21     | 1    | dlc | Data length code (0-8) |
| 22-23  | 2    | terminator | `'\r\n'` |

### Script Flow

1. **Read UART:** `read_uart_frames()` reads 24-byte frames, validates structure, bit-reverses CAN ID, creates `RawFrame` protobuf
2. **Batch:** `batcher()` collects frames until `BATCH_SIZE` or `BATCH_MAX_MS` threshold
3. **Stream:** gRPC client-streaming RPC sends `FrameBatch` messages to bay computer
4. **Acknowledge:** Server returns count of ingested frames when stream closes


## Debugging

### Check UART Data
```bash
cd /home/tonychen/Mridul_gRPC
source .venv/bin/activate
./serial_input.py
```

If no output: verify TEL board connection, check `TEL_UART_PORT`, ensure no port conflicts.

### Check Port Conflicts
```bash
lsof /dev/ttyUSB0
fuser /dev/ttyUSB0
```

### Send Test Frame
```bash
python test_send.py
```

Expected output:
```
Ack frames: 1
```

### Common Issues

**Script won't start:**
- Ensure `cellular_parser` is running on bay computer
- Check for UART port conflicts
- Verify `.env` is loaded

**No data received:**
- Check TEL board power and connection
- Verify `TEL_UART_PORT` is correct
- Confirm user is in `dialout` group

**gRPC connection failed:**
- Verify network connectivity via cellular hotspot
- Check bay computer is reachable: `ping 100.120.214.69`
- Confirm parser container is running: `docker compose ps`


## Tuning Performance

Adjust `.env` for your latency/throughput requirements:

**Low latency:**
```bash
BATCH_SIZE=100
BATCH_MAX_MS=50
```

**High throughput:**
```bash
BATCH_SIZE=500
BATCH_MAX_MS=1000
```

**Compression:**
- `gzip` - recommended, good compression
- `zstd` - faster, requires server support
- `none` - lowest CPU, largest bandwidth


## Quick Reference

### Full Startup Sequence

**Bay Computer:**
```bash
ssh electrical@100.120.214.69
cd /home/electrical/sunlink
source environment/bin/activate
docker compose down && docker compose up -d
```

**Raspberry Pi:**
```bash
ssh sunlite@100.117.111.10
cd /home/tonychen/Mridul_gRPC
source .venv/bin/activate
set -a && source .env && set +a
./rpi_cellular.py
```

### Rebuild Parser Container
```bash
ssh electrical@100.120.214.69
cd /home/electrical/sunlink
docker compose down
docker compose build
docker compose up -d
docker compose ps
```


## Additional Information

- **Server-side parsing:** See sunlink repository for `cellular_parser` documentation
- **CAN parsing and InfluxDB:** Handled entirely on bay computer, not on Pi
- **Protobuf regeneration:** `python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. canlink.proto`

For questions, contact UBC Solar electrical team.
