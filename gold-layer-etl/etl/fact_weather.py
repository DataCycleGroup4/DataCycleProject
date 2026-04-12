import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table
logger = logging.getLogger(__name__)

def load_weather_fact(client, weather_df, humidity_df, temp_df, run_date,
                      time_lookup, humidity_lookup, forecast_lookup, temp_lookup):
    if weather_df.empty:
        return 0
    y, m, d = (int(x) for x in run_date.split("-"))
    hum_vals = {r["time"]: float(r["value_acquired"]) for _, r in humidity_df.iterrows()}
    tmp_vals = {r["time"]: float(r["value_acquired"]) for _, r in temp_df.iterrows()}
    records, seen = [], set()
    for _, row in weather_df.iterrows():
        t = row["time"]
        if t in seen: continue
        seen.add(t)
        h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        hum_id = next((v for k, v in humidity_lookup.items() if k[0] == t), "")
        fc_id = next((v for k, v in forecast_lookup.items() if k[0] == t), "")
        tmp_id = next((v for k, v in temp_lookup.items() if k[0] == t), "")
        fid = hashlib.md5(f"wf_{run_date}_{t}".encode()).hexdigest()
        records.append({"FactID": fid, "TimeID": time_id, "HumidityID": hum_id,
            "ForecastID": fc_id, "TempID": tmp_id, "Most_Recent_Forecast": True,
            "Humidity_Today": hum_vals.get(t), "Temp_Today": tmp_vals.get(t),
            "partition_date": run_date})
    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
    return append_fact_table(client, TABLE_REF["Weather_FactTable"], df, run_date)
