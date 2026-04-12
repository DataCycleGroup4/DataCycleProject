import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_reservation(client, booking_df, run_date):
    if booking_df.empty:
        return {}
    records = []
    for _, row in booking_df.iterrows():
        raw = f"{row['reservation_id']}_{run_date}_{row.get('start_time','')}"
        res_id = hashlib.md5(raw.encode()).hexdigest()
        start_ts = pd.Timestamp(f"{run_date} {row['start_time']}")
        end_ts = pd.Timestamp(f"{run_date} {row['end_time']}")
        records.append({
            "ReservationID": res_id, "Start_time": start_ts, "End_time": end_ts,
            "List_Item": str(row.get("reservation_code", "")),
            "Activity": str(row.get("activity_type", "")),
            "Class": str(row.get("class", "")),
            "Department": str(row.get("department", "")),
            "Professor": str(row.get("instructor", "")),
            "ReservedBy": str(row.get("reserved_by", "")),
        })
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimReservation"], df, "ReservationID")
    lookup = {}
    for i, (_, row_src) in enumerate(booking_df.iterrows()):
        key = f"{row_src['reservation_id']}_{row_src.get('start_time','')}"
        if i < len(df):
            lookup[key] = df.iloc[i]["ReservationID"]
    return lookup
