import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table

logger = logging.getLogger(__name__)

def load_weather_fact(client, weather_df, humidity_df, temp_df, run_date,
                      time_lookup, humidity_lookup, forecast_lookup, temp_lookup):
    if weather_df.empty:
        return 0

    y, m, d = (int(x) for x in run_date.split("-"))
    
    # Pre-map humidity and temperature values for quick access
    hum_vals = {r["time"]: float(r["value_acquired"]) for _, r in humidity_df.iterrows()}
    tmp_vals = {r["time"]: float(r["value_acquired"]) for _, r in temp_df.iterrows()}
    
    records, seen = [], set()
    for _, row in weather_df.iterrows():
        t = row["time"]
        if t in seen: 
            continue
        seen.add(t)
        
        # 1. Align TimeID with DimTime
        h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        
        # 2. Simplified Lookups matching our new Dimension logic
        # Humidity and Temp lookups now use the 'time' string as the key
        hum_id = humidity_lookup.get(t, "")
        tmp_id = temp_lookup.get(t, "")
        
        # Forecast lookup still uses (time, site, measurement)
        fc_id = forecast_lookup.get((t, row["site"], row["measurement"]), "")

        # 3. Create Fact Record
        fid = hashlib.md5(f"wf_{run_date}_{t}_{row['site']}".encode()).hexdigest()
        
        records.append({
            "FactID": fid, 
            "TimeID": time_id, 
            "HumidityID": hum_id,
            "ForecastID": fc_id, 
            "TempID": tmp_id, 
            "Most_Recent_Forecast": True,
            "Humidity_Value": hum_vals.get(t), # Explicit naming for Power BI
            "Temp_Value": tmp_vals.get(t),     # Explicit naming for Power BI
            "partition_date": run_date
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
        
    return append_fact_table(client, TABLE_REF["Weather_FactTable"], df, run_date)