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
        logger.warning(f"No weather data for {run_date}. Skipping fact load.")
        return 0
    
    y, m, d = (int(x) for x in run_date.split("-"))

    # --- Defensive Build for hour-averaged humidity ---
    if not humidity_df.empty and "time" in humidity_df.columns:
        hum_vals = humidity_df.copy()
        hum_vals["hour"] = hum_vals["time"].apply(lambda t: str(t).split(":")[0].zfill(2))
        hum_vals = hum_vals.groupby("hour")["value_acquired"].mean()
    else:
        logger.warning(f"No humidity columns found for {run_date}. Setting defaults.")
        hum_vals = pd.Series(dtype=float)

    # --- Defensive Build for hour-averaged temp ---
    if not temp_df.empty and "time" in temp_df.columns:
        tmp_vals = temp_df.copy()
        tmp_vals["hour"] = tmp_vals["time"].apply(lambda t: str(t).split(":")[0].zfill(2))
        tmp_vals = tmp_vals.groupby("hour")["value_acquired"].mean()
    else:
        logger.warning(f"No temp columns found for {run_date}. Setting defaults.")
        tmp_vals = pd.Series(dtype=float)

    records, seen = [], set()
    for _, row in weather_df.iterrows():
        t = row["time"]
        if t in seen:
            continue
        seen.add(t)

        hour = str(t).split(":")[0].zfill(2)

        # 1. Align TimeID with DimTime safely
        try:
            h, mi, s = (int(x) for x in str(t).split(":"))
            time_id = time_lookup.get((y, m, d, h, mi, s), None)
        except Exception:
            time_id = None

        # 2. Lookups (defaults to None if missing)
        hum_id = humidity_lookup.get(t, None)
        tmp_id = temp_lookup.get(t, None)
        fc_id = forecast_lookup.get((t, row["site"], row["measurement"]), None)

        # 3. Create Fact Record
        fid = hashlib.md5(f"wf_{run_date}_{t}_{row['site']}".encode()).hexdigest()

        # Safely fetch averaged values, handling cases where hour isn't in the index
        h_avg = hum_vals.get(hour, None)
        t_avg = tmp_vals.get(hour, None)

        records.append({
            "FactID": fid,
            "TimeID": time_id,
            "ForecastID": fc_id,
            "Most_Recent_Forecast": True,
            # Ensure float conversion only happens if the value is valid
            "Humidity_Today": float(h_avg) if pd.notna(h_avg) else None,
            "Temp_Today": float(t_avg) if pd.notna(t_avg) else None,
            "partition_date": run_date
        })

    logger.info(f"[DIAG] Built {len(records)} fact records from {len(weather_df)} weather rows")

    df = pd.DataFrame(records)
    if not df.empty:
        # Ensure partition_date is correctly typed for BigQuery
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date

    return append_fact_table(client, TABLE_REF["Weather_FactTable"], df, run_date)