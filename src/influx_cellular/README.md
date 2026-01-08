### Cellular CAN Logger

This script ingests CAN bus data from a USB-CAN adapter, decodes it using a DBC file, and streams it to InfluxDB for real-time telemetry monitoring.

---

## Quick Start

### Prerequisites

Before running this script, ensure the following are set up:

1. **Hardware Connected:**
   - USB-CAN adapter plugged into the Raspberry Pi (typically at `/dev/ttyUSB0`)
   - CAN bus connected to the adapter

2. **Dependencies Installed:**
   
   Run the installation script to set up everything needed for the Pi (Python venv, dependencies, permissions, systemd files):
   
   ```bash
   cd installations
   sudo bash install.sh
   ```
   
   This automatically:
   - Installs Python & system packages
   - Creates a virtual environment
   - Installs all Python dependencies
   - Sets up InfluxDB CLI
   - Configures Tailscale
   - Prepares the cellular logging services

3. **Environment Variables:**
   
   Copy and configure the environment file with your InfluxDB connection details:
   
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   **Required Variables:**
   ```bash
   INFLUX_URL="http://<tailscale-endpoint-ip>:8086"
   INFLUX_ORG="UBC Solar"
   INFLUX_BUCKET="<replace_with_real_bucket>"
   INFLUX_TOKEN="<replace_with_real_token>"
   ```

### Running Manually

To test the script or debug issues, run it manually:

```bash
# From the project root
source .venv/bin/activate
cd src/influx_cellular
python3 cell_script.py
```

**Expected Output:**
```
INFO: CAN ingest loop started.
INFO: Stats: frames_seen=1234 decoded=1200 written=1200 decode_err=20 write_err=0 unknown_ids=14 avg_decoded/s=120.0
```

Press `Ctrl+C` to stop cleanly - the script will flush remaining data to InfluxDB.

### Running as a Service

The script is automatically configured to run as a systemd service after running the installation script. The service runs on startup whenever the RPI has a solid network connection.

**Service Dependencies:**

The service only activates when all 3 requirements are up:
- `network-online.target` - Network interfaces fully up
- `tailscaled.service` - Tailscale VPN connection (if installed)
- `influxdb.service` - InfluxDB service

**Service Management Commands:**

**Start the service:**
```bash
sudo systemctl start cellular-logger
```

**Stop the service temporarily (until next reboot):**
```bash
sudo systemctl stop cellular-logger
```

**Disable the service permanently:**
```bash
sudo systemctl stop cellular-logger
sudo systemctl disable cellular-logger
```

**Enable autorun on every reboot:**
```bash
sudo systemctl enable cellular-logger
```

**Check service status:**
```bash
sudo systemctl status cellular-logger
```

**View live logs:**
```bash
journalctl -u cellular-logger -f
```

**Example Log Output:**
```
Nov 29 20:27:30 sunlite python[4294]: 2025-11-29 20:27:30,396 [WARNING] Retrying (WritesRetry(total=1, connect=None, read=...
Nov 29 20:27:40 sunlite python[4294]: 2025-11-29 20:27:40,409 [WARNING] The retriable error occurred during request. Reas...
```

---

## Configuration

### Script Parameters

Edit these constants in `cell_script.py` if needed:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SERIAL_PORT` | `/dev/ttyUSB0` | Serial port for USB-CAN adapter |
| `BAUDRATE` | `230400` | Serial baud rate |
| `DBC_FILE` | `../../dbc/brightside.dbc` | Path to CAN database file |
| `INF_BATCH_SIZE` | `50` | Points per batch write |
| `INF_FLUSH_INTERVAL_S` | `10.0` | Seconds between forced flushes |
| `USE_NOW_TIME` | `True` | Use system time vs CAN timestamp |

### Serial Device Permissions

If you get a "Permission denied" error on `/dev/ttyUSB0`:

```bash
# Add your user to the dialout group
sudo usermod -a -G dialout $USER

# Then log out and back in, or reboot
```

---

## Understanding the Output

### Statistics Logged Every Second

```
frames_seen=1234    # Total 21-byte frames received from serial
decoded=1200        # Successfully decoded with DBC
written=1200        # Points written to InfluxDB
decode_err=20       # Frames that failed to decode
write_err=0         # Failed InfluxDB writes
unknown_ids=14      # CAN IDs not in the DBC file
avg_decoded/s=120.0 # Ingest rate (frames per second)
```

### Common Issues

**No Data Appearing:**
- Check USB-CAN adapter is connected: `ls /dev/ttyUSB*`
- Verify CAN bus has traffic
- Check InfluxDB connection with `ping <INFLUX_URL>`

**High `decode_errors`:**
- DBC file may be outdated
- Wrong frame layout (script auto-detects both formats)
- Serial baud rate mismatch

**High `write_errors`:**
- InfluxDB server unreachable
- Invalid token or bucket name
- Network connectivity issues

---

## How It Works

The script performs the following pipeline:

1. **Read Serial Data** → Reads chunks from `/dev/ttyUSB0` at 230400 baud
2. **Extract Frames** → Hex-decodes and splits on `\r\n`, extracts 21-byte frames
3. **Parse Frame** → Splits into timestamp (8B), CAN ID (4B), payload (8B)
4. **Decode with DBC** → Uses `cantools` to decode payload into named signals
5. **Create InfluxDB Point** → Converts to time-series format with tags and fields
6. **Batch Write** → Buffers 50 points or 10 seconds, then writes to InfluxDB

```

### InfluxDB Data Model

**Measurement:** CAN module name (e.g., `BMS_Controller`, `Motor_Controller`)  
**Tag:** `class` = DBC message name  
**Fields:** All decoded signals (numeric values only)  
**Timestamp:** System time or embedded CAN timestamp

---

## Technical Implementation

This section provides detailed information about the script's internal architecture for developers who need to modify or extend the code.

### Dependencies

```python
from influxdb_client import InfluxDBClient, Point, WriteOptions
from dotenv import load_dotenv
from datetime import datetime, timezone
import sys, time, signal, struct, logging, serial, cantools, os
```

**Key Libraries:**
- `serial` - Communicates with the USB-CAN adapter
- `cantools` - Loads DBC files and decodes CAN payloads
- `influxdb_client` - Writes time-series data to InfluxDB
- `dotenv` - Loads environment variables from `.env`
- `logging` - Structured logging to stdout (systemd journal)

### Configuration

Environment variables and constants control the script behavior:

    - InfluxDB config is read from environment variables:
        - INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, INFLUX_TOKEN
    - SERIAL_PORT and BAUDRATE define how to talk to the CAN adapter.
    - FRAME_LEN = 21 → each complete CAN record is 21 bytes.
    - CHUNK_SIZE controls how many bytes are read from serial in one go.
    - DBC_FILE is the path to the DBC used for decoding.
    - INF_BATCH_SIZE & INF_FLUSH_INTERVAL_S control Influx batch writing.

    - USE_NOW_TIME:
        - True → timestamps use current system time
        - False → timestamps use the embedded CAN timestamp from the frame

3. #### Setup: Serial, DBC, Influx Client

    #### Serial Port

    ```bash
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1, rtscts=False)
    except Exception as e:
        raise RuntimeError(f"Failed to open {SERIAL_PORT}: {e}")
    ```

    - Opens the serial port at 230400 baud.
    - timeout=1 → read() returns at least once per second.
    - If the port can’t be opened, the script throws a RuntimeError and exits.

    #### DBC Database

    ```bash
    db = cantools.database.load_file(DBC_FILE)
    ```

    - Loads all CAN message definitions from the DBC file.
    - Used later for ID → message lookup and payload decode.

    #### Influx Client and Write API

    ```bash
    client = InfluxDBClient(
        url=INFLUX_URL,
        org=INFLUX_ORG,
        token=INFLUX_TOKEN,
        enable_gzip=False,
    )

    write_api = client.write_api(
        write_options=WriteOptions(
            batch_size=INF_BATCH_SIZE,
            flush_interval=int(INF_FLUSH_INTERVAL_S * 1000),
            jitter_interval=100,
            retry_interval=5000,
            max_retries=5,
            max_retry_delay=30_000,
            exponential_base=2,
        )
    )
    ```

    - Uses the official InfluxDB v2 Python client.
    - Batches points:
        - max INF_BATCH_SIZE per batch
        - flush every INF_FLUSH_INTERVAL_S seconds
    - Retries on write failures with exponential backoff.

4. #### Timestamp Parsing

    ```bash
    def parse_timestamp_seconds(ts8: bytes) -> float:
        try:
            return float(struct.unpack(">d", ts8)[0])
        except Exception:
            pass
        try:
            return float(struct.unpack(">Q", ts8)[0])
        except Exception:
            pass
        try:
            ms = struct.unpack(">Q", ts8)[0]
            return float(ms) / 1000.0
        except Exception:
            pass
        return struct.unpack(">d", ts8)[0]
    ```

    Given an 8-byte timestamp field, the script tries multiple interpretations:
    1. Big-endian double (>d) → float seconds
    2. Big-endian unsigned 64-bit int seconds (>Q)
    3. Big-endian unsigned 64-bit int milliseconds (>Q then / 1000)
    4. Fallback to big-endian double again if everything fails

5. #### DBC Message Caching and Decode

    ```bash
    _MSG_CACHE: dict[int, cantools.database.can.message.Message | None] = {}
    DBC_IDS: set[int] = set(m.frame_id for m in db.messages)
    ```

    - _MSG_CACHE caches frame_id → message definition to avoid repeated lookups.
    - DBC_IDS is the set of all CAN IDs defined in the DBC.

    #### ID to Message Lookup

    ```bash
    def _get_db_message(can_id: int):
    msg = _MSG_CACHE.get(can_id)
    if msg is None:
        try:
            msg = db.get_message_by_frame_id(can_id)
        except KeyError:
            msg = None
        _MSG_CACHE[can_id] = msg
    return msg
    ```

    - Fast, cached lookup.
    - Returns None if ID is not in the DBC (unknown message).

    ```bash
    def try_decode_layout(raw21: bytes, layout: str):
        if layout == "with_filler":
            ts_bytes, id_bytes, data_bytes = raw21[0:8], raw21[9:13], raw21[13:21]
        elif layout == "no_filler":
            ts_bytes, id_bytes, data_bytes = raw21[0:8], raw21[8:12], raw21[12:20]
        else:
            raise ValueError("Unknown layout")
    ```

    The script supports two possible frame layouts for the 21-byte record:
    1. with_filler – there’s 1 “filler” byte between timestamp and ID
    2. no_filler – timestamp and ID are back-to-back

    For each layout:
    - Extracts ts_bytes, id_bytes, data_bytes
    - Parses timestamp with parse_timestamp_seconds
    - Converts CAN ID from bytes → int
    - Looks up DBC message
    - Decodes payload via cantools

    ```bash
    ts_seconds = parse_timestamp_seconds(ts_bytes)
    can_id = int.from_bytes(id_bytes, "big")
    msg = _get_db_message(can_id)

    if msg is None:
        raise KeyError(f"CAN ID 0x{can_id:X} not in DBC")

    measurements = msg.decode(bytearray(data_bytes))
    sources = getattr(msg, "senders", []) or []
    source = sources[0] if sources else "UNKNOWN"
    cls_name = msg.name
    ```

    - Then returning the can_id, source, cls_name, ts_seconds, measurements

    #### Layout Fallback Message

    ```bash
    def decode_frame(raw21: bytes):
        try:
            return try_decode_layout(raw21, "with_filler")
        except Exception:
            return try_decode_layout(raw21, "no_filler")
    ```

    - First tries with_filler.
    - If that fails (e.g., decode error), falls back to no_filler.

6. #### Influx Point Creation and Write

    #### Building a Point

    ```bash
    def make_point(source: str, cls_name: str, ts_seconds: float, measurements: dict) -> Point:
    if USE_NOW_TIME:
        ts_influx = datetime.now(timezone.utc)
    else:
        ts_influx = datetime.fromtimestamp(ts_seconds, tz=timezone.utc)

    p = Point(source).tag("class", cls_name)

    for name, val in measurements.items():
        if isinstance(val, bool):
            val = 1.0 if val else 0.0
        elif not isinstance(val, (int, float)):
            continue
        p.field(name, float(val))

    p.field("can_timestamp", float(ts_seconds))
    p.time(ts_influx)
    return p
    ```

    - Measurement name = source (e.g., ECU / module name from DBC senders)
    - Adds a tag: class = message_name (DBC message name)
    - For each decoded signal:
        - Bool → 0.0 or 1.0
        - Only numeric fields are stored
    - Adds can_timestamp field with original float timestamp
    - Timestamp used in Influx is either:
        - now (if USE_NOW_TIME=True)
        - decoded timestamp (if False)

    #### Writing and Error Tracking

    ```bash
    def write_to_influx(source: str, cls_name: str,
                    ts_seconds: float, measurements: dict,
                    counters: dict):
    try:
        point = make_point(source, cls_name, ts_seconds, measurements)
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        counters["written"] += 1
    except Exception as e:
        counters["write_errors"] += 1
        if counters["write_errors"] <= 10 or counters["write_errors"] % 1000 == 0:
            logging.warning(
                "Influx write error (count=%d): %r",
                counters["write_errors"], e
            )
    ```

    - On success: counters["written"] increments.
    - On failure:
        - write_errors increments
        - Logs first 10 errors and then every 1000th error (to avoid log spam)

7. #### Hex Chunk Splitting and Frame Extraction

    The serial port returns binary bytes. The logger expects hex-encoded lines ending with \r\n (0d0a in hex).

    ```bash
    _HEX_OK = set("0123456789abcdefABCDEF")
    ```

    ```bash
    def process_message(message_hex: str, buffer_hex: str = ""):
        s = buffer_hex + message_hex
        parts = s.split("0d0a")
        buffer_hex = parts.pop() if parts else ""
        frames: list[bytes] = []
    ```

    Logic:
    1. Prepend leftover buffer_hex to new message_hex chunk.
    2. Split on line delimiter 0d0a (CRLF).
    3. The last part may be incomplete → saved as new buffer_hex.

    Then for each full segment:
    - Strips spaces.
    - Ignores segments shorter than 42 hex chars (21 bytes).
    - Slides across the string in 42-char steps and validates:
        - Only valid hex chars
        - bytes.fromhex(seg) succeeds

    Valid frames are appended to frames as raw 21-byte objects.
    
    Returns the frames, buffer_hex

8. #### Counters and Shutdown

    #### Counters

    ```bash
    counters = {
        "frames_seen":   0,
        "decoded":       0,
        "written":       0,
        "decode_errors": 0,
        "write_errors":  0,
        "unknown_ids":   0,
    }
    ```

    These track:
    - How many frames were seen from the serial stream
    - How many were successfully decoded and written
    - How many decode/write errors occurred
    - How many CAN IDs were not found in the DBC

    #### Shutdown Handler

    ```bash
    def _shutdown(*_):
    try:
        logging.info("Shutting down, flushing Influx...")
        write_api.flush()
        elapsed = max(time.time() - _start_time, 1e-6)
        logging.info(
            "FINAL STATS: frames_seen=%d decoded=%d written=%d "
            "decode_errors=%d write_errors=%d unknown_ids=%d "
            "uptime=%.1fs avg_decoded/s=%.1f",
            ...
        )
    finally:
        ...
        sys.exit(0)
    ```

    - On SIGINT/SIGTERM:
        - Flushes remaining Influx data
        - Logs final stats
        - Closes write_api, client, and serial port
        - Exits cleanly

    Signals wired:

    ```bash
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    ```

9. #### Main Ingest Loop

    ```bash
    def run():
    global _last_log
    logging.info("CAN ingest loop started.")
    buffer_hex = ""

    while True:
        chunk = ser.read(CHUNK_SIZE)
    ```

    #### Handling No Data

    If chunk is empty:
    - Once per second, logs current stats:
        - frames_seen, decoded, written
        - decode_err, write_err, unknown_ids
        - avg_decoded/s (ingest rate)
    - Then continues the loop.

    #### Processing Data

    - Convert raw bytes to a hex string.
    - Pass into process_message with leftover hex buffer.
    - Get back:
        - A list of 21-byte frames
        - Updated buffer_hex tail

    For each raw21 frame:
    1. frames_seen++
    2. Try to decode:

    ```bash
        try:
        can_id, source, cls_name, ts_seconds, measurements = decode_frame(raw21)
    except KeyError:
        counters["decode_errors"] += 1
        counters["unknown_ids"] += 1
        continue
    except Exception as e:
        counters["decode_errors"] += 1
        ...
        continue
    ```

    3. On success:
        - decoded++
        - write_to_influx(...) called → possibly updates written or write_errors
    
    #### Periodic Stats Log

    At the end of each loop iteration:
    - If ≥ 1 second since last log:
        - Compute ingest_rate = decoded / elapsed
        - Log all counters + ingest rate
        - Update _last_log

10. #### Script Entry

    ```bash
    if __name__ == "__main__":
        try:
            run()
        except KeyboardInterrupt:
            _shutdown()
    ```

    - When run directly (or as a systemd service), run() starts the ingest loop.
    - Ctrl+C / KeyboardInterrupt calls _shutdown() for a clean exit.