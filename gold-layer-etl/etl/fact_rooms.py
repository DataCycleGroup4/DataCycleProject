import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table
logger = logging.getLogger(__name__)

def load_rooms_fact(client, booking_df, run_date, time_lookup, room_lookup, reservation_lookup):
    if booking_df.empty:
        return 0
    y, m, d = (int(x) for x in run_date.split("-"))
    total_rooms = booking_df["room_id"].nunique()
    records = []
    for time_str, group in booking_df.groupby("start_time"):
        parts = time_str.split(":")
        h, mi = int(parts[0]), int(parts[1])
        time_id = time_lookup.get((y, m, d, h, mi, 0), "")
        booked = group["room_id"].nunique()
        pct = booked / total_rooms if total_rooms > 0 else 0
        free = total_rooms - booked
        for _, row in group.iterrows():
            rid = room_lookup.get(row["room_id"], 0)
            rkey = f"{row['reservation_id']}_{row.get('start_time','')}"
            resid = reservation_lookup.get(rkey)
            fid = hashlib.md5(f"rf_{run_date}_{time_str}_{row['room_id']}_{row['reservation_id']}".encode()).hexdigest()
            records.append({"FactID": fid, "TimeID": time_id, "RoomID": rid,
                "ReservationID": resid, "Pct_Rooms_Booked": pct,
                "Rooms_Free_Count": free, "partition_date": run_date})
    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
    return append_fact_table(client, TABLE_REF["Rooms_FactTable"], df, run_date)
