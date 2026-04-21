import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def generate_time_id(year, month, day, hour, minute, second):
    # Standardized ISO format for hashing to ensure Fact tables can replicate the ID
    raw = f"{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"
    return hashlib.md5(raw.encode()).hexdigest()

def build_dim_time(all_timestamps):
    records, seen = [], set()
    for ts in all_timestamps:
        # Rounding or extracting components to ensure uniqueness at the second level
        key = (ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second)
        if key in seen:
            continue
        seen.add(key)
        
        records.append({
            "TimeID": generate_time_id(*key),
            "Year": ts.year, 
            "Month": ts.month, 
            "Day": ts.day,
            "Hour": ts.hour, 
            "Minute": ts.minute, 
            "Second": ts.second,
        })
    return pd.DataFrame(records)

def load_dim_time(client, all_timestamps):
    if not all_timestamps:
        logger.warning("No timestamps provided to load_dim_time.")
        return {}

    df = build_dim_time(all_timestamps)
    

    
    upsert_dim_table(client, TABLE_REF["DimTime"], df, "TimeID")
    
    # Return lookup dictionary: (y, m, d, h, mi, s) -> TimeID
    lookup = {
        (row["Year"], row["Month"], row["Day"], row["Hour"], row["Minute"], row["Second"]): row["TimeID"]
        for _, row in df.iterrows()
    }
    return lookup