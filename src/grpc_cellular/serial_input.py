#!/usr/bin/env python3
import serial, binascii

PORT = "/dev/ttyUSB0"
BAUD = 230400         # ← TEL uses 230400
ser = serial.Serial(port=PORT, baudrate=BAUD, timeout=0.2)

while True:
    chunk = ser.read(1024)     # read raw bytes, not lines
    if chunk:
        print(binascii.hexlify(chunk, sep=b" ").decode())
