import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_room(client, booking_df):
    if booking_df.empty:
        return {}

    # 1. Deduplicate rooms
    rooms = booking_df[["room_id"]].drop_duplicates().copy()
    
    records = []
    for _, row in rooms.iterrows():
        rid_str = str(row["room_id"])
        
        # Create a STABLE ID using MD5 instead of the unstable hash()
        # We take the first 8 characters of the hex for a clean integer-like string ID
        # or just use the full hex. Let's stay consistent with your other dims.
        stable_id = hashlib.md5(rid_str.encode()).hexdigest()
        
        records.append({
            "RoomID": stable_id,
            "Alt_RoomID": rid_str, 
            "FullName": rid_str, 
            "Alt_FullName": rid_str,
        })

    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimRoom"], df, "RoomID")

    # 2. Return lookup for fact_rooms.py
    return {row["Alt_RoomID"]: row["RoomID"] for _, row in df.iterrows()}