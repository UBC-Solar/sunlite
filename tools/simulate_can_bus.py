import can
import time
import yaml
import signal
import threading
from   pathlib import Path
import datetime
import sys

ANSI_YELLOW = "\033[33m"
ANSI_RESET = "\033[0m"
RATE_SCALER = 1
MSG_COUNT_IDX = 3

global can_messages
can_messages = {}

bus_lock = threading.Lock()

TOTAL_SENT = 0

STOP_EVENT = threading.Event()

def get_rtc_data():
    """
    Get the current time and format it into an 8-byte data payload.
    The first six bytes are:
      Byte 0: Second
      Byte 1: Minute
      Byte 2: Hour
      Byte 3: Day
      Byte 4: Month
      Byte 5: Year (last two digits)
    Byte 6 and 7 are reserved and set to zero.
    """
    now = datetime.datetime.now() + datetime.timedelta(hours=7)
    sec    = now.second        & 0xFF  # Byte 0
    minute = now.minute        & 0xFF  # Byte 1
    hour   = now.hour          & 0xFF  # Byte 2
    day    = now.day           & 0xFF  # Byte 3
    month  = now.month         & 0xFF  # Byte 4
    year   = (now.year % 100)  & 0xFF  # Byte 5 (e.g., 2025 -> 25)
    
    data = bytearray(8)
    data[0] = sec
    data[1] = minute
    data[2] = hour
    data[3] = day
    data[4] = month
    data[5] = year
    data[6] = 0  # Reserved
    data[7] = 0  # Reserved
    
    print("gei", sec, minute, hour, day, month, year)
    return data

def load_can_messages(filename):
    path = Path(__file__).parent / filename # Use Path to handle the file path
    
    with open(path, 'r') as file:
        messages = yaml.safe_load(file)
        
    for msg in messages:
        can_id = str(msg['ID'])
        interval = msg['interval'] / 1000.0
        data = [int(msg['data'][i:i+2], 16) for i in range(0, len(msg['data']), 2)]
        dlc = msg['dlc']  # Data Length Code
        board_delay = msg['board_delay'] / 1000.0
        num_in_burst = msg['num_msgs_sent_in_burst']
        count = 0
        can_messages[can_id] = [interval, data, dlc, count, board_delay, num_in_burst]

def signal_handler(sig, frame):
    STOP_EVENT.set()
    print(ANSI_YELLOW + "\nExiting... Here are the message counts:" + ANSI_RESET)
    total_count = 0
    
    for can_id, message_data in can_messages.items():
        count = message_data[MSG_COUNT_IDX]
        total_count += count
        print(ANSI_YELLOW  + f"ID: {can_id}, Count: {count}" + ANSI_RESET)
        
    print(ANSI_YELLOW + f"Total count: {total_count}" + ANSI_RESET)

def send_message(bus, can_id, data, rate, dlc, board_delay, num_in_burst):
    global TOTAL_SENT
    time.sleep(board_delay)
    is_extended = False if int(can_id[2:], 16) <= 0x7FF else True

    while not STOP_EVENT.is_set():
        try:
            if (int(can_id[2:], 16) == 0x300):
                data = get_rtc_data()
                dlc = 8  # Data Length Code for 8 bytes.
                message = can.Message(
                    arbitration_id=int(can_id, 16),
                    data=data[:dlc],
                    is_extended_id=is_extended
                )
            else:
                message = can.Message(arbitration_id=int(can_id, 16), data=data[:dlc], is_extended_id=is_extended)
                
            for _ in range(num_in_burst):
                if STOP_EVENT.is_set():
                    break

                with bus_lock:
                    bus.send(message)
                    can_messages[can_id][MSG_COUNT_IDX] += 1
                    TOTAL_SENT += 1
                    print(f"ID: {can_id}, Count: {can_messages[can_id][MSG_COUNT_IDX]}, Total: {TOTAL_SENT}")

                    for _ in range(1):
                        if STOP_EVENT.is_set():
                            break
                        time.sleep(0.001)
                        
        except can.CanError as e:
            print(f"Message NOT sent {e}")

        for _ in range(10):
            if STOP_EVENT.is_set():
                break
            time.sleep(rate * RATE_SCALER / 10.0)
            
def send_can_messages():
    # FOR UBUNTU PEOPLE
    # bus = can.interface.Bus(channel='can0', bustype='socketcan')
    
    # FOR WINDOWS PEOPLE Use PCAN-USB adapter
    bus = can.interface.Bus(
        channel='PCAN_USBBUS1',   # first USB adapter
        bustype='pcan'
    )
    
    load_can_messages('can_messages.yaml')
    
    threads = []
    for can_id, (interval, data, dlc, count, board_delay, num_in_burst) in can_messages.items():
        thread = threading.Thread(
            target=send_message,
            args=(bus, can_id, data, interval, dlc, board_delay, num_in_burst),
            daemon=True
        )
        thread.start()
        threads.append(thread)

    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.2)
            if STOP_EVENT.is_set():
                break
    except KeyboardInterrupt:
        STOP_EVENT.set()
    sys.exit(0)
    
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except Exception:
        pass
    send_can_messages()