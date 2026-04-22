import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table

logger = logging.getLogger(__name__)

def _normalize_time(t) -> str:
    """Ensures time is always HH:MM:SS."""
    s = str(t).strip()
    parts = s.split(":")
    if len(parts) == 2: s = f"{s}:00"
    if len(parts) == 1: s = f"{s.zfill(2)}:00:00"
    return s.zfill(8)

def load_rooms_fact(client, booking_df, run_date, time_lookup, room_lookup, reservation_lookup):
    # 1. FILTER: Since Silver files are weekly/monthly, we must extract only today's data
    day_df = booking_df[booking_df["date"] == run_date].copy()
    
    if day_df.empty:
        logger.warning(f"No booking data found for date {run_date} in the provided files.")
        return 0

    y, m, d = (int(x) for x in run_date.split("-"))
    total_rooms = len(room_lookup)
    records = []

    # 2. GROUPING: Grouping by start_time is correct for a Galaxy Schema snapshot
    for time_str, group in day_df.groupby("start_time"):
        norm_t = _normalize_time(time_str)
        parts = norm_t.split(":")
        h, mi, s = int(parts[0]), int(parts[1]), int(parts[2])
        
        # Consistent lookup with dim_time.py
        time_id = time_lookup.get((y, m, d, h, mi, s)) 
        
        booked_count = group["room_id"].nunique()
        pct_booked = booked_count / total_rooms if total_rooms > 0 else 0
        free_count = total_rooms - booked_count

        for _, row in group.iterrows():
            rid = room_lookup.get(str(row["room_id"]))
            
            # Lookup key matches the dictionary key in dim_reservation.py
            rkey = f"{row['reservation_id']}_{row.get('start_time','')}"
            resid = reservation_lookup.get(rkey)

            # 3. INTEGRITY CHECK: Critical because TimeID and RoomID are REQUIRED in BQ
            if not time_id or not rid:
                logger.error(f"SKIPPING ROW: Missing ID for Room:{row['room_id']} or Time:{norm_t}")
                continue

            # Create FactID
            fid_raw = f"rf_{run_date}_{norm_t}_{row['room_id']}_{row['reservation_id']}"
            fid = hashlib.md5(fid_raw.encode()).hexdigest()

            records.append({
                "FactID": fid, 
                "TimeID": time_id, 
                "RoomID": rid,
                "ReservationID": resid if resid else "", 
                "Pct_Rooms_Booked": float(pct_booked),
                "Rooms_Free_Count": int(free_count), 
                "partition_date": run_date
            })

    logger.info(f"[DIAG] Built {len(records)} room fact records for {run_date}")

    if not records:
        return 0

    df = pd.DataFrame(records)
    df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
    return append_fact_table(client, TABLE_REF["Rooms_FactTable"], df, run_date)