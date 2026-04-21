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
    # Deduplicate by reservation_id and start_time to ensure unique dim rows
    unique_bookings = booking_df.drop_duplicates(subset=['reservation_id', 'start_time']).copy()

    for _, row in unique_bookings.iterrows():
        # Create a consistent unique ID for the reservation
        raw = f"res_{row['reservation_id']}_{row.get('start_time','')}"
        res_id = hashlib.md5(raw.encode()).hexdigest()
        
        # Combine date and time for Power BI timeline support
        start_ts = pd.to_datetime(f"{run_date} {row['start_time']}")
        end_ts = pd.to_datetime(f"{run_date} {row['end_time']}")
        
        records.append({
            "ReservationID": res_id, 
            "Start_time": start_ts, 
            "End_time": end_ts,
            "List_Item": str(row.get("reservation_code", "")),
            "Activity": str(row.get("activity_type", "")),
            "Class": str(row.get("class", "")),
            "Department": str(row.get("department", "")),
            "Professor": str(row.get("instructor", "")),
            "ReservedBy": str(row.get("reserved_by", "")),
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimReservation"], df_to_load, "ReservationID")

    # Build the lookup: Map the source natural keys to the surrogate hash ID
    lookup = {}
    for _, row in booking_df.iterrows():
        # This string MUST match the 'raw' variable above exactly
        raw_key = f"res_{row['reservation_id']}_{row.get('start_time','')}"
        res_id = hashlib.md5(raw_key.encode()).hexdigest()
        
        # We use the natural key (ID + Time) as the dictionary key for the fact table
        lookup[f"{row['reservation_id']}_{row.get('start_time','')}"] = res_id
        
    return lookup