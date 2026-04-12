import pandas as pd
from google.cloud import storage
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def read_parquet_from_gcs(bucket_name: str, prefix: str) -> pd.DataFrame:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    parquet_blobs = [b for b in blobs if b.name.endswith(".parquet")]
    if not parquet_blobs:
        logger.warning(f"No parquet files at gs://{bucket_name}/{prefix}")
        return pd.DataFrame()
    frames = []
    for blob in parquet_blobs:
        data = blob.download_as_bytes()
        df = pd.read_parquet(BytesIO(data))
        frames.append(df)
        logger.info(f"Read {len(df)} rows from gs://{bucket_name}/{blob.name}")
    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Total rows from {prefix}: {len(combined)}")
    return combined

def resolve_silver_path(path_template: str, run_date: str) -> str:
    month = run_date[5:7]
    return path_template.format(month=month, date=run_date)
