import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_consumption(client, consumption_df, run_date):
    if consumption_df.empty:
        return {}

    # 1. Deduplicate: Get unique value/variation pairs
    # We remove 'time' so we only store the unique profiles of consumption
    unique_df = consumption_df[['value_acquired', 'variation']].drop_duplicates().copy()

    records = []
    for _, row in unique_df.iterrows():
        # Hash ONLY the attributes. 
        # This makes the ID permanent for a specific reading value.
        raw = f"cons_profile_{row['value_acquired']}_{row['variation']}"
        cid = hashlib.md5(raw.encode()).hexdigest()
        
        records.append({
            "ConsumptionID": cid,
            "Value": float(row["value_acquired"]),
            "Variation": float(row["variation"])
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimConsumption"], df_to_load, "ConsumptionID")

    # 2. Build the Lookup: Map the TIME back to the unique ID
    # This allows fact_power.py to link the specific time to the right consumption profile
    lookup = {}
    for _, row in consumption_df.iterrows():
        # Re-generate the hash for this specific row's values
        raw = f"cons_profile_{row['value_acquired']}_{row['variation']}"
        cid = hashlib.md5(raw.encode()).hexdigest()
        
        # We use a tuple (time, value) as the key to ensure an exact match in the fact table
        lookup[(row["time"], str(row["value_acquired"]))] = cid

    return lookup