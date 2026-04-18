import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_humidity(client, humidity_df, run_date):
    if humidity_df.empty:
        return {}

    # 1. Deduplicate: Only keep unique value/variation combinations
    # We remove 'time' to ensure the Dimension is small and clean.
    unique_df = humidity_df[['value_acquired', 'variation']].drop_duplicates().copy()

    records = []
    for _, row in unique_df.iterrows():
        # Hash ONLY the attributes. This creates a "Conformed" ID.
        # '49.46' will always result in the same ID regardless of when it happened.
        raw = f"hum_lvl_{row['value_acquired']}_{row['variation']}"
        hid = hashlib.md5(raw.encode()).hexdigest()
        
        records.append({
            "HumidityID": hid,
            "Value": float(row["value_acquired"]),
            "Variation": float(row["variation"])
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimHumidity"], df_to_load, "HumidityID")

    # 2. Build the Lookup for the Weather Fact table
    # This maps the specific timestamp back to the unique HumidityID
    lookup = {}
    for _, row in humidity_df.iterrows():
        # Re-generate the same hash used for the dimension
        raw = f"hum_lvl_{row['value_acquired']}_{row['variation']}"
        hid = hashlib.md5(raw.encode()).hexdigest()
        
        # We use 'time' as the primary key for the lookup so fact_weather can find it
        lookup[row["time"]] = hid

    return lookup