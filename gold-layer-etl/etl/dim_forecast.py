import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_forecast(client, weather_df, run_date):
    if weather_df.empty:
        return {}

    # 1. Deduplicate: Get unique Site/Measurement/Unit combinations
    # We remove 'time', 'value', and 'prediction' because those change constantly
    # and belong in the Fact table.
    unique_forecasts = weather_df[['site', 'measurement', 'unit']].drop_duplicates().copy()

    records = []
    for _, row in unique_forecasts.iterrows():
        # Hash ONLY the site and measurement to create a permanent ID
        raw = f"fc_def_{row['site']}_{row['measurement']}"
        fid = hashlib.md5(raw.encode()).hexdigest()
        
        records.append({
            "ForecastID": fid,
            "Site": str(row["site"]),
            "Measurement": str(row["measurement"]),
            "Unit": str(row["unit"])
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimForecast"], df_to_load, "ForecastID")

    # 2. Build the Lookup for fact_weather.py
    # This maps the (time, site, measurement) back to the static ForecastID
    lookup = {}
    for _, row in weather_df.iterrows():
        # Re-generate the same hash used for the dimension
        raw = f"fc_def_{row['site']}_{row['measurement']}"
        fid = hashlib.md5(raw.encode()).hexdigest()
        
        # Use a tuple that matches what fact_weather.py will use to find this ID
        lookup[(row["time"], row["site"], row["measurement"])] = fid

    return lookup