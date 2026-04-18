import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def _normalize_time(t) -> str:
    s = str(t).strip()
    parts = s.split(":")
    if len(parts) == 2:
        s = f"{s}:00"
    return s.zfill(8)

def load_dim_humidity(client, humidity_df, run_date):
    if humidity_df.empty:
        return {}

    unique_df = humidity_df[['value_acquired', 'variation']].drop_duplicates().copy()
    records = []
    for _, row in unique_df.iterrows():
        raw = f"hum_lvl_{row['value_acquired']}_{row['variation']}"
        hid = hashlib.md5(raw.encode()).hexdigest()
        records.append({
            "HumidityID": hid,
            "Value":      float(row["value_acquired"]),
            "Variation":  float(row["variation"])
        })
    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimHumidity"], df_to_load, "HumidityID")

    lookup = {}
    for _, row in humidity_df.iterrows():
        raw = f"hum_lvl_{row['value_acquired']}_{row['variation']}"
        hid = hashlib.md5(raw.encode()).hexdigest()
        lookup[_normalize_time(row["time"])] = hid  # normalized key to match fact_weather
    return lookup