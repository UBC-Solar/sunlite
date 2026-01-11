# test_send.py
import time, grpc
from tools.proto import canlink_pb2, canlink_pb2_grpc

SERVER = "100.120.214.69:50051"   # elec-bay Tailscale IP:port

def req_iter():
    batch = canlink_pb2.FrameBatch()
    f = batch.frames.add()
    f.timestamp = time.time()
    f.can_id = 0x701          # known from your DBC dump
    f.is_extended_id = False  # 0x701 is 11-bit
    f.data = bytes([1,2,3,4,5,6,7,8])
    f.dlc = 8
    yield batch                # stream-unary: must yield an iterator

channel = grpc.insecure_channel(
    SERVER,
    options=[
        ("grpc.max_send_message_length", 50*1024*1024),
        ("grpc.max_receive_message_length", 50*1024*1024),
    ],
)
stub = canlink_pb2_grpc.CanIngestStub(channel)

ack = stub.UploadFrames(req_iter(), compression=grpc.Compression.Gzip)
print("Ack frames:", ack.frames_ingested)

