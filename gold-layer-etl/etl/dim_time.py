import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def generate_time_id(year, month, day, hour, minute, second):
    raw = f"{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
    return hashlib.md5(raw.encode()).hexdigest()

def build_dim_time(all_timestamps):
    records, seen = [], set()
    for ts in all_timestamps:
        key = (ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second)
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "TimeID": generate_time_id(*key),
            "Year": ts.year, "Month": ts.month, "Day": ts.day,
            "Hour": ts.hour, "Minute": ts.minute, "Second": ts.second,
        })
    return pd.DataFrame(records)

def load_dim_time(client, all_timestamps):
    df = build_dim_time(all_timestamps)
    upsert_dim_table(client, TABLE_REF["DimTime"], df, "TimeID")
    lookup = {}
    for _, row in df.iterrows():
        key = (row["Year"], row["Month"], row["Day"], row["Hour"], row["Minute"], row["Second"])
        lookup[key] = row["TimeID"]
    return lookup
