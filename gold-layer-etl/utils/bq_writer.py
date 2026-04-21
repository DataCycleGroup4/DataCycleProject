import pandas as pd
from google.cloud import bigquery
import logging

logger = logging.getLogger(__name__)

def get_bq_client(location: str = "EU") -> bigquery.Client:
    return bigquery.Client(location=location)

def upsert_dim_table(client, table_ref, df, key_column):
    if df.empty:
        logger.info(f"No data to upsert into {table_ref}")
        return 0
    query = f"SELECT `{key_column}` FROM `{table_ref}`"
    existing_keys = set()
    try:
        result = client.query(query).result()
        existing_keys = {row[0] for row in result}
    except Exception as e:
        logger.warning(f"Could not fetch existing keys from {table_ref}: {e}")
    new_rows = df[~df[key_column].isin(existing_keys)]
    if new_rows.empty:
        logger.info(f"No new rows for {table_ref}")
        return 0
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = client.load_table_from_dataframe(new_rows, table_ref, job_config=job_config)
    job.result()
    logger.info(f"Inserted {len(new_rows)} new rows into {table_ref}")
    return len(new_rows)

def append_fact_table(client, table_ref, df, partition_date):
    if df.empty:
        logger.info(f"No data to append to {table_ref}")
        return 0
    delete_query = f"DELETE FROM `{table_ref}` WHERE partition_date = '{partition_date}'"
    try:
        client.query(delete_query).result()
        logger.info(f"Cleared partition {partition_date} in {table_ref}")
    except Exception as e:
        logger.warning(f"Could not clear partition in {table_ref}: {e}")
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    logger.info(f"Appended {len(df)} rows to {table_ref} (partition={partition_date})")
    return len(df)
