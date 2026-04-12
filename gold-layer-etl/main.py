import logging
import sys
import pandas as pd
from config import RUN_DATE, BUCKET_NAME, SILVER_PATHS, LOCATION
from utils.gcs_reader import read_parquet_from_gcs, resolve_silver_path
from utils.bq_writer import get_bq_client
from etl.dim_time import load_dim_time
from etl.dim_reservation import load_dim_reservation
from etl.dim_room import load_dim_room
from etl.dim_consumption import load_dim_consumption
from etl.dim_humidity import load_dim_humidity
from etl.dim_temp import load_dim_temp
from etl.dim_inverter import load_dim_inverter
from etl.dim_errors import load_dim_errors
from etl.dim_forecast import load_dim_forecast
from etl.dim_consumption_prediction import load_dim_consumption_prediction
from etl.dim_production_prediction import load_dim_production_prediction
from etl.fact_power import load_power_fact
from etl.fact_weather import load_weather_fact
from etl.fact_rooms import load_rooms_fact
from etl.fact_prediction import load_prediction_fact

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("gold-etl")

def collect_timestamps(run_date, *dataframes_with_time_col):
    y, m, d = (int(x) for x in run_date.split("-"))
    timestamps = []
    for df, time_col in dataframes_with_time_col:
        if df.empty:
            continue
        for _, row in df.iterrows():
            t = str(row[time_col])
            parts = t.split(":")
            h, mi = int(parts[0]), int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            timestamps.append(pd.Timestamp(year=y, month=m, day=d, hour=h, minute=mi, second=s))
    return timestamps

def main():
    run_date = RUN_DATE
    logger.info(f"=== Gold Layer ETL START for {run_date} ===")
    client = get_bq_client(LOCATION)

    # 1. Read silver layer
    logger.info("Reading silver layer data from GCS...")
    booking_df = read_parquet_from_gcs(BUCKET_NAME, resolve_silver_path(SILVER_PATHS["booking"], run_date))
    consumption_df = read_parquet_from_gcs(BUCKET_NAME, resolve_silver_path(SILVER_PATHS["powerconsumption"], run_date))
    humidity_df = read_parquet_from_gcs(BUCKET_NAME, resolve_silver_path(SILVER_PATHS["humidity"], run_date))
    temp_df = read_parquet_from_gcs(BUCKET_NAME, resolve_silver_path(SILVER_PATHS["temperature"], run_date))
    production_df = read_parquet_from_gcs(BUCKET_NAME, resolve_silver_path(SILVER_PATHS["production"], run_date))
    weather_df = read_parquet_from_gcs(BUCKET_NAME, resolve_silver_path(SILVER_PATHS["weather"], run_date))

    if all(df.empty for df in [booking_df, consumption_df, humidity_df, temp_df, production_df, weather_df]):
        logger.warning(f"No data found for {run_date}. Exiting.")
        return

    # 2. Build DimTime from all timestamps
    logger.info("Building DimTime...")
    all_ts = collect_timestamps(run_date,
        (booking_df, "start_time"), (consumption_df, "time"), (humidity_df, "time"),
        (temp_df, "time"), (production_df, "time"), (weather_df, "time"))
    time_lookup = load_dim_time(client, all_ts)

    # 3. Load dimension tables
    logger.info("Loading dimension tables...")
    reservation_lookup = load_dim_reservation(client, booking_df, run_date)
    room_lookup = load_dim_room(client, booking_df)
    consumption_lookup = load_dim_consumption(client, consumption_df, run_date)
    humidity_lookup = load_dim_humidity(client, humidity_df, run_date)
    temp_lookup = load_dim_temp(client, temp_df, run_date)
    inverter_lookup = load_dim_inverter(client, production_df, run_date)
    error_lookup = load_dim_errors(client, production_df, run_date)
    forecast_lookup = load_dim_forecast(client, weather_df, run_date)
    cons_pred_lookup = load_dim_consumption_prediction(client, consumption_df, run_date)
    prod_pred_df = load_dim_production_prediction(client, weather_df, run_date)

    # 4. Load fact tables
    logger.info("Loading fact tables...")
    load_power_fact(client, production_df, consumption_df, run_date,
                    time_lookup, consumption_lookup, inverter_lookup, error_lookup)
    load_weather_fact(client, weather_df, humidity_df, temp_df, run_date,
                      time_lookup, humidity_lookup, forecast_lookup, temp_lookup)
    load_rooms_fact(client, booking_df, run_date, time_lookup, room_lookup, reservation_lookup)
    load_prediction_fact(client, run_date, time_lookup, cons_pred_lookup, prod_pred_df, consumption_df)

    logger.info(f"=== Gold Layer ETL COMPLETE for {run_date} ===")

if __name__ == "__main__":
    main()
