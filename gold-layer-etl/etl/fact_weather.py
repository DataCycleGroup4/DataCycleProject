import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table

logger = logging.getLogger(__name__)


def _normalize_time(t) -> str:
    """Normalize a time value to 'HH:MM:SS' string for consistent key matching."""
    s = str(t).strip()
    parts = s.split(":")
    if len(parts) == 2:
        s = f"{s}:00"
    return s.zfill(8)  # ensures 'H:MM:SS' -> '0H:MM:SS'


def load_weather_fact(client, weather_df, humidity_df, temp_df, run_date,
                      time_lookup, humidity_lookup, forecast_lookup, temp_lookup):
    if weather_df.empty:
        return 0
    y, m, d = (int(x) for x in run_date.split("-"))

    # Build hour-averaged humidity and temp values
    hum_vals = humidity_df.copy()
    hum_vals["hour"] = hum_vals["time"].apply(lambda t: t.split(":")[0].zfill(2))
    hum_vals = hum_vals.groupby("hour")["value_acquired"].mean()

    tmp_vals = temp_df.copy()
    tmp_vals["hour"] = tmp_vals["time"].apply(lambda t: t.split(":")[0].zfill(2))
    tmp_vals = tmp_vals.groupby("hour")["value_acquired"].mean()

    records, seen = [], set()
    for _, row in weather_df.iterrows():
        t = row["time"]
        if t in seen:
            continue
        seen.add(t)

        hour = t.split(":")[0].zfill(2)

        # 1. Align TimeID with DimTime
        h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")

        # 2. Lookups
        hum_id = humidity_lookup.get(t, "")
        tmp_id = temp_lookup.get(t, "")
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
            "Humidity_Today": float(hum_vals.get(hour, pd.NA)),
            "Temp_Today": float(tmp_vals.get(hour, pd.NA)),
            "partition_date": run_date
        })

    logger.info(f"[DIAG] Built {len(records)} fact records from {len(weather_df)} weather rows")

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date

    return append_fact_table(client, TABLE_REF["Weather_FactTable"], df, run_date)