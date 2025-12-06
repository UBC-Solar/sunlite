# Sunlite RPi gRPC Cellular Client

This repository contains the **Raspberry Pi client** for Sunlite’s cellular telemetry pipeline.

On the Pi, we:

- Open a UART connection to the telemetry (TEL) board  
- Parse each fixed-size CAN frame into a protobuf `RawFrame`  
- Batch frames into `FrameBatch` messages (by size and time)  
- Stream those batches over **gRPC** to the remote parser (`cellular_parser` on the bay computer)

In short:

`UART → parse → protobuf (RawFrame) → batch (FrameBatch) → gRPC stream`


## High-Level Data Flow

1. TEL board sends 24-byte binary frames over UART.
2. `rpi_cellular.py`:
   - Reads raw bytes from `/dev/ttyUSB0` (or whatever port is configured).
   - Validates frame structure and parses timestamp, CAN ID, data, and DLC.
   - Converts the frame into a protobuf `RawFrame` message.
3. Frames are batched into `FrameBatch` messages using:
   - `BATCH_SIZE` (max frames per batch)
   - `BATCH_MAX_MS` (max time before flushing a partially full batch)
4. The Pi opens a gRPC client-streaming RPC to the **bay computer**:
   - Host: `electrical@100.120.214.69`
   - Service: `cellular_parser` Docker container on port `50051`
5. The Pi streams `FrameBatch` messages continuously until stopped.
6. When the stream ends, the server replies with an acknowledgment (how many frames were ingested).


## Repository Layout (RPi Side)

Typical layout (RPi side only):

```text
sunlite/
├── rpi_cellular.py         # Main RPi client script (UART → gRPC → bay computer)
├── serial_input.py         # Simple UART debug script (print raw frames)
├── test_send.py            # Send a test CAN frame to the server
├── .env                    # Runtime configuration (UART, batching, server addr, etc.)
└── tools/
    └── proto/
        ├── canlink.proto
        ├── canlink_pb2.py
        └── canlink_pb2_grpc.py


Note: canlink_pb2.py and canlink_pb2_grpc.py are generated from canlink.proto using grpcio-tools.
If you ever need to regenerate them, you can do so with a protoc command from this directory (not shown here).

Prerequisites

On the Raspberry Pi:

Raspberry Pi 4B (or similar) running Raspberry Pi OS (64-bit, Bookworm recommended)

Python 3.10+

A working UART connection to the TEL board (typically /dev/ttyUSB0)

Network connectivity (via LTE/5G hotspot or wired LAN) to the bay computer:

Host: electrical@100.120.214.69

cellular_parser Docker container listening on port 50051

The generated protobuf modules (canlink_pb2, canlink_pb2_grpc) available under tools/proto

Environment Variables

Runtime configuration is provided through environment variables (often via a .env file in the repo root, e.g. /home/sunlite/sunlite/.env).

Example .env
# RPi client runtime config
TEL_UART_PORT=/dev/serial/by-id/usb-FTDI_C232HM-DDHSL-0_FT1K72V9-if00-port0
TEL_UART_BAUD=230400

# gRPC endpoint of the parser (bay computer IP:port, cellular_parser container)
INGEST_SERVER=100.120.214.69:50051

# batching
BATCH_SIZE=200
BATCH_MAX_MS=50

# compression
GRPC_COMP=gzip

Variable Reference

TEL_UART_PORT
UART device used to talk to the TEL board.
Examples:

/dev/ttyUSB0

/dev/serial/by-id/... for a stable device path.

TEL_UART_BAUD
CAN telemetry baud rate (e.g. 230400).

INGEST_SERVER
gRPC endpoint of the parser on the bay computer:
e.g. 100.120.214.69:50051 (where the cellular_parser container is listening).

BATCH_SIZE
Max number of frames per FrameBatch.

Once this many frames are collected, a batch is sent immediately.

Needs tuning: larger batches = better throughput but higher latency.

BATCH_MAX_MS
Max time (in milliseconds) before flushing a partial batch.

If we have not reached BATCH_SIZE within this time window, we send the batch anyway.

Also needs tuning: larger window = more batching, but more latency.

GRPC_COMP
Compression mode for gRPC:

"gzip" – compress batches with gzip (recommended on the Pi).

"zstd" – if enabled and supported by the server.

"none" – no compression.

Loading .env on the Pi

One simple way to export these before running the script:

cd /home/sunlite/sunlite
set -a
source .env
set +a

Installing on the Raspberry Pi
1. Clone the repo onto the Pi
cd ~
git clone https://github.com/UBC-Solar/sunlite.git
cd sunlite

2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

Assuming you have a requirements.txt in the repo:

pip install -r requirements.txt

4. Create and edit your .env
cp .env.example .env   # if an example file exists
nano .env              # set TEL_UART_PORT, INGEST_SERVER, etc.

5. Ensure the UART device is accessible

The USB–UART adapter should appear (e.g. /dev/ttyUSB0 or the /dev/serial/by-id/... path).

You may need to add the sunlite user to the dialout group:

sudo usermod -aG dialout sunlite

Running the RPi gRPC Client

Make sure the cellular_parser Docker container is running on the bay computer (100.120.214.69:50051) before starting the Pi client.

From the repo root on the Pi:

cd /home/sunlite/sunlite
source .venv/bin/activate

# load environment if not exported anywhere else
set -a
source .env
set +a

# run the RPi client
./rpi_cellular.py     # if executable
# or:
python rpi_cellular.py


You should see output similar to:

[RPi] UART open on /dev/ttyUSB0@230400, streaming to 100.120.214.69:50051
[RPi] stream closed, server ack: 773661 frames

How rpi_cellular.py Works

At a high-level, the script is structured as follows:

1. UART Frame Layout and Parsing

Each TEL UART frame is 24 bytes:

uint64 timestamp bits (big-endian, interpreted as a double)

char '#' delimiter

uint32 CAN ID (bit-reversed in TEL; we reverse it back on the Pi)

uint8[8] CAN data bytes

uint8 DLC (data length code, 0–8)

'\r' '\n' terminator

read_uart_frames(ser):

Continuously reads raw bytes from ser.read(...) into a buffer.

When it has at least 24 bytes:

Checks the last two bytes are \r\n (otherwise it drops one byte and resyncs).

Parses timestamp, delimiter, CAN ID, data, DLC.

Rejects frames with invalid delimiter or DLC > 8.

Bit-reverses the CAN ID back into standard form.

Converts the timestamp bits to a Python float using _double_from_be_uint64.

Builds and yields a canlink_pb2.RawFrame protobuf.

2. Batching Frames

batcher(frame_iter, batch_size, max_ms):

Collects RawFrame messages into an in-memory queue.

Flushes them as a canlink_pb2.FrameBatch when:

The queue size reaches batch_size, or

max_ms milliseconds have passed since the last flush.

Yields FrameBatch messages downstream.

3. gRPC Streaming

run():

Opens the UART port with:

ser = serial.Serial(UART_PORT, UART_BAUD, timeout=0)


Chooses gRPC compression based on GRPC_COMP (gzip, zstd, or none).

Creates an insecure gRPC channel to SERVER_ADDR (from INGEST_SERVER).

Builds a CanIngestStub from canlink_pb2_grpc.

Defines req_iter() generator:

def req_iter():
    for batch in batcher(read_uart_frames(ser), BATCH_SIZE, BATCH_MAX_MS):
        yield batch


Calls the client-streaming RPC:

ack = stub.UploadFrames(req_iter(), compression=compression)


The server processes the stream, writes decoded data to InfluxDB (on the server side), then replies with an UploadAck telling how many frames it ingested.

The script prints that count and exits when the stream closes.

Debugging on the Pi
1. Check That UART Is Receiving Data

Use serial_input.py to see raw CAN frames coming in:

cd /home/sunlite/sunlite
source .venv/bin/activate

set -a
source .env
set +a

./serial_input.py


You should see raw frames or some debug representation of the incoming data.

If you see no output:

Verify the TEL board is powered and connected.

Verify the correct UART device is set in TEL_UART_PORT.

Make sure nothing else is using the port (see below).

2. Check for Conflicts on /dev/ttyUSB0

If another process has the port open, the client will not read properly:

lsof /dev/ttyUSB0
fuser /dev/ttyUSB0


Kill or stop any conflicting processes before running rpi_cellular.py.

3. Send a Test CAN Message

Use test_send.py to send a single test frame to the server via the same gRPC pipeline:

cd /home/sunlite/sunlite
source .venv/bin/activate

set -a
source .env
set +a

python test_send.py


You should see an acknowledgment similar to:

Ack frames: 1


If the ack is not received:

Verify INGEST_SERVER is correct (e.g. 100.120.214.69:50051).

Check that the cellular_parser container is running on the bay computer.

Tuning Batching and Compression

You can tune the trade-off between latency and throughput using the .env:

BATCH_SIZE

Larger values → fewer gRPC messages, better throughput, but higher per-frame latency.

Smaller values → lower latency but more overhead.

BATCH_MAX_MS

Smaller values → flush partial batches more often, lower latency, but less batching.

Larger values → better batching, higher average latency.

A good starting point:

BATCH_SIZE=200
BATCH_MAX_MS=50
GRPC_COMP=gzip


From there, you can experiment (e.g., larger BATCH_MAX_MS up to ~1000 ms if throughput is more important than latency).
