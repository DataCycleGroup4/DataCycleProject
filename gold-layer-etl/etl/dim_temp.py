import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_temp(client, temp_df, run_date):
    if temp_df.empty:
        return {}

    # 1. Deduplicate: Unique temperature value/variation pairs only
    # This prevents the "1,000 rows" bloat and makes the Dim a true lookup
    unique_df = temp_df[['value_acquired', 'variation']].drop_duplicates().copy()

    records = []
    for _, row in unique_df.iterrows():
        # Static hash based on the attributes, not the time
        raw = f"temp_lvl_{row['value_acquired']}_{row['variation']}"
        tid = hashlib.md5(raw.encode()).hexdigest()
        
        records.append({
            "TempID": tid,
            "Value": float(row["value_acquired"]),
            "Variation": float(row["variation"])
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimTemp"], df_to_load, "TempID")

    # 2. Build the Lookup: Map the TIME back to the stable TempID
    # This allows the Weather Fact table to find the ID easily
    lookup = {}
    for _, row in temp_df.iterrows():
        raw = f"temp_lvl_{row['value_acquired']}_{row['variation']}"
        tid = hashlib.md5(raw.encode()).hexdigest()
        
        # We use 'time' as the key to match the lookup pattern in fact_weather.py
        lookup[row["time"]] = tid

    return lookup