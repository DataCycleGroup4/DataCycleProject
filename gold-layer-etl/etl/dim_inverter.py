import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_inverter(client, production_df, run_date):
    if production_df.empty:
        return {}

    # 1. Deduplicate to get unique Inverters only
    # We only care about the ID and its static properties
    # Change this line:
    unique_inverters = production_df[['inv_id']].drop_duplicates().copy() 

# And remove 'Status' from the dimension if it changes frequently; 
# keep it in the Fact table instead.
    records = []
    for _, row in unique_inverters.iterrows():
        # Hash ONLY the Inverter ID so the key is permanent and unique
        raw = f"inv_{row['inv_id']}"
        inv_key = hashlib.md5(raw.encode()).hexdigest()
        
        records.append({
            "InverterKey": inv_key,
            "InverterID": int(row["inv_id"]),
            "Status": str(row["status"])
            # Note: PAC, Daysum, PDC are MEASURES, they belong in the Fact table, not here.
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimInverter"], df_to_load, "InverterKey")

    # 2. Build the Lookup for fact_power.py
    # This tells the Fact table: "For this specific row/time, use this InverterKey"
    lookup = {}
    for _, row in production_df.iterrows():
        # Re-generate the same hash based on the ID to map it back
        raw = f"inv_{row['inv_id']}"
        inv_key = hashlib.md5(raw.encode()).hexdigest()
        # Key the lookup by (time, inv_id) so the Fact table can find it
        lookup[(row["time"], str(row["inv_id"]))] = inv_key

    return lookup