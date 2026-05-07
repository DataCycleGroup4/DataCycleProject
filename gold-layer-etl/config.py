import os
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

PROJECT_ID  = os.environ["GCP_PROJECT"]
DATASET_ID  = os.environ["BQ_DATASET"]
BUCKET_NAME = os.environ["GCS_BUCKET"]
LOCATION    = os.environ.get("BQ_LOCATION", "EU")

# Calculate yesterday's date, then shift back 3 years to match the 2023 data
yesterday = datetime.utcnow() - timedelta(days=1)
RUN_DATE = os.environ.get(
    "RUN_DATE",
    (yesterday - timedelta(days=3*365)).strftime("%Y-%m-%d")
)

SILVER_PATHS = {
    "booking": "processed/cleanbellevuebooking/{month}/",
    "humidity": "processed/cleanbellevueconso/cleanhumidity/{month}/date={date}/",
    "powerconsumption": "processed/cleanbellevueconso/cleanpowerconsumption/{month}/date={date}/",
    "temperature": "processed/cleanbellevueconso/cleantemperature/{month}/date={date}/",
    "production": "processed/cleansolarlogs/cleanproduction/{month}/date={date}/",
    "weather": "processed/cleanweather/{month}/date_partition={date}/",
}

TABLE_REF = {table: f"{PROJECT_ID}.{DATASET_ID}.{table}" for table in [
    "DimTime", "DimReservation", "DimRoom", "DimConsumption",
    "DimHumidity", "DimTemp", "DimInverter", "DimErrors",
    "DimForecast", "DimConsumptionPrediction", "DimProductionPredictionPac", "DimProductionPredictionDaysum",
    "Power_FactTable", "Weather_FactTable", "Rooms_FactTable",
    "Prediction_FactTable",
]}
