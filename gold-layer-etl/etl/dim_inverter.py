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
    unique_inverters = production_df[['inv_id']].drop_duplicates().copy() 

    records = []
    for _, row in unique_inverters.iterrows():
        raw = f"inv_{row['inv_id']}"
        inv_key = hashlib.md5(raw.encode()).hexdigest()
        
        records.append({
            "InverterKey": inv_key,
            "InverterID": int(row["inv_id"])
            # Note: PAC, Daysum, PDC are MEASURES, they belong in the Fact table, not here.
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimInverter"], df_to_load, "InverterKey")

    # 2. Build the Lookup for fact_power.py
    lookup = {}
    for _, row in production_df.iterrows():
        raw = f"inv_{row['inv_id']}"
        inv_key = hashlib.md5(raw.encode()).hexdigest()
        lookup[(row["time"], str(row["inv_id"]))] = inv_key

    return lookup