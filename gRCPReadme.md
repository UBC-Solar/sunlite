# Sunlite RPi gRPC Cellular Client

This repository contains the **Raspberry Pi client** for Sunlink's cellular telemetry pipeline.

The Pi reads 24-byte CAN frames from the TEL board via UART, converts them to protobuf messages, batches them, and streams them over gRPC to the `cellular_parser` on the bay computer.

**UART -> Raspberry Pi -> protobuf -> batch -> gRPC stream**

**Note:** The Pi does NOT parse CAN frames. It only forwards raw data. All parsing (DBC decoding, InfluxDB writing) happens on the bay computer.


## Architecture
```
┌─────────────┐        UART          ┌──────────────────────────┐
│  TEL Board  │ ───────────────────> │  Raspberry Pi (sunlite)  │
│             │   (24-byte frames)   │                          │
└─────────────┘                      │  rpi_cellular.py         │
                                     │  - Read UART             │
                                     │  - Convert to protobuf   │
                                     │  - Zip & Batch           │
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
├── .env.example                  # Example configuration (copy to .env locally)
├── requirements.txt              # Python dependencies
├── src/
│   └── grpc_cellular/
│       ├── rpi_cellular.py       # Main client script
│       ├── serial_input.py       # Debug: view raw UART frames
│       └── test_send.py          # Debug: send test frame to server
└── tools/
    └── proto/
        ├── canlink.proto
        ├── canlink_pb2.py
        └── canlink_pb2_grpc.py
```

**Important:** Run commands from the repo root (`sunlite/`) with `-m` flag. The scripts import `tools.proto.*`.


## Prerequisites

### Hardware
- Raspberry Pi 4B with Raspberry Pi OS (64-bit, Bookworm) with an SD card
- USB-UART adapter (e.g., FTDI C232HM-DDHSL-0)
- LTE/5G cellular hotspot + SIM Card
- TEL board connected via UART

### Software
- Python 3.10+
- Network connectivity to bay computer (`100.120.214.69:50051`)
- `cellular_parser` Docker container running on bay computer (Sunlink side)

**Note:** The Sunlite and Bay Computer IP might change. More on this later.

## Installation (RPi)

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
pip install --upgrade pip
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
BATCH_SIZE=1000
BATCH_MAX_MS=1000

# Compression
GRPC_COMP=gzip
```

**Tip: Find the correct UART device path**

If `/dev/serial/by-id/...` doesn't exist on your Pi, list available devices:
```bash
ls -l /dev/serial/by-id/
ls -l /dev/ttyUSB*
```

Then set `TEL_UART_PORT` accordingly.


## Configuration Variables

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `TEL_UART_PORT` | UART device path | `/dev/ttyUSB0` | Use `/dev/serial/by-id/...` for stable path |
| `TEL_UART_BAUD` | Baud rate | `230400` | Must match TEL board |
| `INGEST_SERVER` | gRPC endpoint | `100.120.214.69:50051` | Bay computer parser |
| `BATCH_SIZE` | Frames per batch | `1000` | Tune for latency/throughput |
| `BATCH_MAX_MS` | Max batch time (ms) | `1000` | Flush interval |
| `GRPC_COMP` | Compression mode | `gzip` | Options: `gzip`, `none` |


## Running the Client

### Step 1: Start Bay Computer Parser (Required — do this first)
```bash
ssh electrical@100.120.214.69

cd /home/electrical/sunlink
source environment/bin/activate

docker compose down
docker compose up -d
```

**(Optional sanity check on bay computer)**
```bash
docker compose ps
```

### Step 2: Start RPi Client

Run from the repo root (`sunlite/`):
```bash
ssh sunlite@100.117.111.10

cd /home/sunlite/sunlite
source .venv/bin/activate

set -a
source .env
set +a

python -m src.grpc_cellular.rpi_cellular
```

Expected output:
```
[RPi] UART open on /dev/ttyUSB0@230400, streaming to 100.120.214.69:50051
[RPi] stream closed, server ack: 773661 frames
```


## Debugging

### 1. Send a test frame (no UART required)

This tests Pi -> gRPC -> parser connectivity. Run from repo root:
```bash
python -m src.grpc_cellular.test_send
```

Expected output:
```
Ack frames: 1
```

### 2. Check UART data (requires TEL + adapter)
```bash
python -m src.grpc_cellular.serial_input
```

If no output: verify TEL board connection, check `TEL_UART_PORT`, ensure no port conflicts.

### 3. Check port conflicts
```bash
lsof /dev/ttyUSB0
fuser /dev/ttyUSB0
```

### 4. Check IP addresses

The IP addresses for the Raspberry Pi (sunlite) and bay computer may change. Both devices are on the Tailscale network. To verify current IP addresses:
```bash
tailscale status
```

Update `INGEST_SERVER` in `.env` if the bay computer IP has changed.

### Common Issues

**`ModuleNotFoundError: No module named 'tools'`**
- Run scripts from repo root using `python -m ...` commands as shown above.

**UART device path not found**
- The FTDI path in `.env` may not match your Pi. Use:
```bash
  ls -l /dev/serial/by-id/
  ls -l /dev/ttyUSB*
```
  and update `TEL_UART_PORT`.

**gRPC connection failed**
- Check bay computer is reachable:
```bash
  ping 100.120.214.69
```
- Confirm parser container is running on bay computer:
```bash
  docker compose ps
```


## Tuning Performance

Adjust `.env` for your latency/throughput requirements:

**Lower latency:**
```bash
BATCH_SIZE=200
BATCH_MAX_MS=50
```

**Higher throughput / better bandwidth efficiency:**
```bash
BATCH_SIZE=2000
BATCH_MAX_MS=2000
```

**Compression:**
- `gzip` - recommended (raw CAN frames compress well)
- `none` - lowest CPU, highest bandwidth use


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
cd /home/sunlite/sunlite
source .venv/bin/activate
set -a && source .env && set +a
python -m src.grpc_cellular.rpi_cellular
```

### Rebuild Parser Container (bay computer)
```bash
ssh electrical@100.120.214.69
cd /home/electrical/sunlink
docker compose down
docker compose build
docker compose up -d
docker compose ps
```


## Additional Information

- **CAN parsing and InfluxDB:** Handled entirely on bay computer, not on Pi.
- **Protobuf regeneration (optional):**
```bash
  python -m grpc_tools.protoc \
    -I tools/proto \
    --python_out=tools/proto \
    --grpc_python_out=tools/proto \
    tools/proto/canlink.proto
```


## How the Architecture Works (and How the Code Works)

### Big-picture dataflow (end-to-end)

1. TEL board produces raw CAN frames and sends them out over UART in a fixed 24-byte format.

2. Pi reads UART bytes, slices them into 24-byte records, and validates each record (delimiter + `\r\n`).

3. Each UART record is converted into a protobuf `RawFrame` containing:
   - timestamp
   - can_id
   - dlc
   - data[:dlc]

4. The Pi groups frames into `FrameBatch` messages using:
   - `BATCH_SIZE` (flush once N frames collected)
   - `BATCH_MAX_MS` (flush after T ms even if not full)

5. The Pi streams these batches to the server over one long-lived gRPC connection (`UploadFrames`).

6. The server receives batches, decodes CAN IDs using the DBC, turns decoded signals into InfluxDB points, and writes them to InfluxDB.

7. When the stream ends, the server returns an ack (e.g., `frames_ingested`) back to the Pi.

### Why gRPC streaming

- Binary protobuf messages (efficient over cellular).
- HTTP/2 streaming: avoids repeated request overhead and allows continuous, ordered delivery.
- Compression (gzip) is very effective on raw CAN payloads.

### Code Walkthrough (Pi Side)

**`rpi_cellular.py` main responsibilities:**

**(1) UART ingest**
- Opens UART using:
  - `TEL_UART_PORT`
  - `TEL_UART_BAUD`

**(2) Frame parsing**
- Continuously reads bytes from serial.
- Maintains a buffer and extracts fixed-size 24-byte frames.
- Validates:
  - frame ends with `\r\n`
  - delimiter byte is `#`
  - dlc <= 8
- Extracts fields:
  - timestamp bytes [0:8] (interpreted as big-endian double)
  - CAN ID bytes [9:13]
  - data bytes [13:21]
  - dlc byte [21]

**(3) Protobuf conversion**
- Converts each UART record into `canlink_pb2.RawFrame(...)`.

**(4) Batching**
- Collects `RawFrame` into a queue.
- Flushes to `FrameBatch` when:
  - queue size reaches `BATCH_SIZE`, OR
  - elapsed time reaches `BATCH_MAX_MS`

**(5) gRPC upload**
- Creates a gRPC stub: `CanIngestStub(channel)`
- Defines a generator that yields `FrameBatch` messages.
- Calls:
```python
  stub.UploadFrames(generator, compression=...)
```

**`test_send.py` (parser connectivity test)**
- Does not require UART.
- Builds one `FrameBatch` with one `RawFrame`.
- Streams it to the parser and expects:
```
  Ack frames: 1
```

**`serial_input.py` (UART visibility)**
- Debug helper to confirm you are receiving well-formed raw UART frames before involving gRPC.
