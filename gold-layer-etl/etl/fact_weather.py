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

    # Pre-map humidity and temperature values using normalized time keys
    hum_vals = {_normalize_time(r["time"]): float(r["value_acquired"]) for _, r in humidity_df.iterrows()}
    tmp_vals = {_normalize_time(r["time"]): float(r["value_acquired"]) for _, r in temp_df.iterrows()}

    # --- DIAGNOSTIC ---
    weather_times = {_normalize_time(t) for t in weather_df["time"]}
    hum_overlap   = len(weather_times & set(hum_vals))
    tmp_overlap   = len(weather_times & set(tmp_vals))
    hum_id_hits   = sum(1 for t in weather_times if t in humidity_lookup)
    tmp_id_hits   = sum(1 for t in weather_times if t in temp_lookup)

    logger.info(f"[DIAG] weather_df rows: {len(weather_df)}, unique times: {len(weather_times)}")
    logger.info(f"[DIAG] humidity_df rows: {len(humidity_df)}, temp_df rows: {len(temp_df)}")
    logger.info(f"[DIAG] Sample weather times:       {sorted(list(weather_times))[:3]}")
    logger.info(f"[DIAG] Sample humidity_lookup keys: {sorted(list(humidity_lookup.keys()))[:3]}")
    logger.info(f"[DIAG] Sample temp_lookup keys:     {sorted(list(temp_lookup.keys()))[:3]}")
    logger.info(f"[DIAG] Sample hum_vals keys:        {sorted(list(hum_vals.keys()))[:3]}")
    logger.info(f"[DIAG] Sample tmp_vals keys:        {sorted(list(tmp_vals.keys()))[:3]}")
    logger.info(f"[DIAG] hum_vals overlap (values):   {hum_overlap}/{len(weather_times)}")
    logger.info(f"[DIAG] tmp_vals overlap (values):   {tmp_overlap}/{len(weather_times)}")
    logger.info(f"[DIAG] humidity_lookup hits (IDs):  {hum_id_hits}/{len(weather_times)}")
    logger.info(f"[DIAG] temp_lookup hits (IDs):      {tmp_id_hits}/{len(weather_times)}")

    if hum_overlap == 0:
        logger.error("[DIAG] ZERO hum_vals hits — humidity values will all be None")
    if tmp_overlap == 0:
        logger.error("[DIAG] ZERO tmp_vals hits — temp values will all be None")
    if hum_id_hits == 0:
        logger.error("[DIAG] ZERO humidity_lookup hits — HumidityID will all be empty")
    if tmp_id_hits == 0:
        logger.error("[DIAG] ZERO temp_lookup hits — TempID will all be empty")
    # --- END DIAGNOSTIC ---

    records, seen = [], set()
    for _, row in weather_df.iterrows():
        t_raw = row["time"]
        t = _normalize_time(t_raw)

        # Deduplicate on full grain (time + site + measurement)
        grain = (t, row["site"], row["measurement"])
        if grain in seen:
            continue
        seen.add(grain)

        # 1. Align TimeID with DimTime
        h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        if not time_id:
            logger.warning(f"No TimeID found for {y}-{m}-{d} {h}:{mi:02d}:{s:02d}")

        # 2. Humidity and Temp lookups using normalized time key
        hum_id = humidity_lookup.get(t, "")
        tmp_id = temp_lookup.get(t, "")
        if not hum_id:
            logger.warning(f"No HumidityID for time={t}")
        if not tmp_id:
            logger.warning(f"No TempID for time={t}")

        # 3. Forecast lookup uses (time, site, measurement)
        fc_id = forecast_lookup.get((t, row["site"], row["measurement"]), "")
        if not fc_id:
            logger.warning(f"No ForecastID for time={t}, site={row['site']}, measurement={row['measurement']}")

        # 4. Retrieve values using normalized key
        hum_val = hum_vals.get(t)
        tmp_val = tmp_vals.get(t)
        if hum_val is None:
            logger.warning(f"No humidity value for time={t}")
        if tmp_val is None:
            logger.warning(f"No temp value for time={t}")

        # 5. FactID now reflects full grain (time + site + measurement)
        fid = hashlib.md5(f"wf_{run_date}_{t}_{row['site']}_{row['measurement']}".encode()).hexdigest()

        records.append({
            "FactID":               fid,
            "TimeID":               time_id,
            "HumidityID":           hum_id,
            "ForecastID":           fc_id,
            "TempID":               tmp_id,
            "Most_Recent_Forecast": True,
            "Humidity_Value":       hum_val,
            "Temp_Value":           tmp_val,
            "partition_date":       run_date
        })

    logger.info(f"[DIAG] Built {len(records)} fact records from {len(weather_df)} weather rows")

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
        null_hum = df["HumidityID"].eq("").sum()
        null_tmp = df["TempID"].eq("").sum()
        null_hum_val = df["Humidity_Value"].isna().sum()
        null_tmp_val = df["Temp_Value"].isna().sum()
        logger.info(f"[DIAG] Final df — missing HumidityID: {null_hum}, TempID: {null_tmp}, "
                    f"Humidity_Value: {null_hum_val}, Temp_Value: {null_tmp_val}")

    return append_fact_table(client, TABLE_REF["Weather_FactTable"], df, run_date)