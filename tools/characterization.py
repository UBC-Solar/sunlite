import pandas as pd
from zoneinfo import ZoneInfo

csv_path = "tools/<filename>.csv" # Replace with the path to the selected CSV

# Use the local start and end time
start_local = "2025-11-25 21:58:00"
end_local   = "2025-11-25 21:59:00"

local_tz = "America/Vancouver" # Change based on the exact timezone the script was activated

df = pd.read_csv(csv_path, comment="#", low_memory=False)

time_col = "_time"

if time_col not in df.columns:
    print(0)
    raise SystemExit(0)
 
df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)

# Converts the start times to UTC
start_utc = pd.to_datetime(start_local).replace(tzinfo=ZoneInfo(local_tz)).astimezone(ZoneInfo("UTC"))
end_utc   = pd.to_datetime(end_local).replace(tzinfo=ZoneInfo(local_tz)).astimezone(ZoneInfo("UTC"))

mask = (df[time_col] >= start_utc) & (df[time_col] <= end_utc)
print(int(mask.sum()))