import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table

logger = logging.getLogger(__name__)

def load_rooms_fact(client, booking_df, run_date, time_lookup, room_lookup, reservation_lookup):
    if booking_df.empty:
        return 0

    y, m, d = (int(x) for x in run_date.split("-"))
    total_rooms_in_system = len(room_lookup) # Total rooms known to the dimension

    records = []
    for time_str, group in booking_df.groupby("start_time"):
        parts = time_str.split(":")
        h, mi = int(parts[0]), int(parts[1])
        s = 0 # Defaulting to 0 to match DimTime's grain
        
        # 1. Lookup the IDs
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        
        booked_count = group["room_id"].nunique()
        pct_booked = booked_count / total_rooms_in_system if total_rooms_in_system > 0 else 0
        free_count = total_rooms_in_system - booked_count

        for _, row in group.iterrows():
            # Match the room ID from our stable dim_room (MD5 hex)
            rid = room_lookup.get(str(row["room_id"]), "")
            
            # Match the reservation key exactly as defined in dim_reservation lookup
            rkey = f"{row['reservation_id']}_{row.get('start_time','')}"
            resid = reservation_lookup.get(rkey, "")

            # Unique Fact ID
            fid_raw = f"rf_{run_date}_{time_str}_{row['room_id']}_{row['reservation_id']}"
            fid = hashlib.md5(fid_raw.encode()).hexdigest()

            records.append({
                "FactID": fid, 
                "TimeID": time_id, 
                "RoomID": rid,
                "ReservationID": resid, 
                "Pct_Rooms_Booked": float(pct_booked),
                "Rooms_Free_Count": int(free_count), 
                "partition_date": run_date
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
        
    return append_fact_table(client, TABLE_REF["Rooms_FactTable"], df, run_date)