import os
from datetime import datetime, timedelta

PROJECT_ID = os.environ.get("GCP_PROJECT", "project-d31bc18d-8d9f-48db-a77")
DATASET_ID = os.environ.get("BQ_DATASET", "DataCycle_Warehouse")
BUCKET_NAME = os.environ.get("GCS_BUCKET", "data-cycle-lake")
LOCATION = os.environ.get("BQ_LOCATION", "EU")

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
