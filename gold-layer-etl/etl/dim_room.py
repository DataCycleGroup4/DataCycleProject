import pandas as pd
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_room(client, booking_df):
    if booking_df.empty:
        return {}
    rooms = booking_df[["room_id"]].drop_duplicates()
    records = []
    for _, row in rooms.iterrows():
        rid = str(row["room_id"])
        records.append({
            "RoomID": abs(hash(rid)) % (10**9),
            "Alt_RoomID": rid, "FullName": rid, "Alt_FullName": rid,
        })
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimRoom"], df, "RoomID")
    return {r["Alt_RoomID"]: r["RoomID"] for _, r in df.iterrows()}
