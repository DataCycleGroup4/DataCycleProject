import pandas as pd
import os
import gcsfs
import logging

# Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"
BUCKET = "data-cycle-lake"  
BRONZE_BASE = f"gs://{BUCKET}/raw/bellevueconso/weather"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanbellevueconso/cleanweather"   

# Initialize GCS
try:
    fs = gcsfs.GCSFileSystem(token=SERVICE_ACCOUNT_KEY)
    logging.info("Authenticated successfully.")
except Exception as e:
    logging.critical(f"Auth failed: {e}")
    exit()

for month in range(1, 13):
    month_str = str(month).zfill(2)
    bronze_glob = f"{BRONZE_BASE}/{month_str}/*.csv*"
    
    try:
        files = fs.glob(bronze_glob)
        if not files:
            logging.info(f"Month {month_str}: No files found.")
            continue

        df_list = []
        for f in files:
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            try:
                chunk = pd.read_csv(
                    full_path, 
                    storage_options={"token": SERVICE_ACCOUNT_KEY},
                    sep=None, 
                    engine='python', 
                    encoding='utf-16',
                    on_bad_lines='skip',
                    skipinitialspace=True
                )
                if not chunk.empty:
                    df_list.append(chunk)
            except Exception as read_e:
                logging.warning(f"Skipping file {f}: {read_e}")
        
        if not df_list:
            continue
            
        df = pd.concat(df_list, ignore_index=True)

        # 3. Transform & Clean
        # Renaming by position to handle weird encoding characters in headers
        df = df.rename(columns={
            df.columns[0]: 'time',
            df.columns[1]: 'value',
            df.columns[2]: 'prediction',
            df.columns[3]: 'site',
            df.columns[4]: 'measurement',
            df.columns[5]: 'unit'

        })

        # Fix European decimals (comma to dot) and dates
        df['time_dt'] = pd.to_datetime(df['time'], format='%d.%m.%Y', errors='coerce')
        for col in ['value', 'prediction']:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace(',', '.', regex=False)
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['variation'] = pd.to_numeric(df['variation'], errors='coerce')

        # Filter for quality
        mask = (df['time_dt'].notna()) & (df['value'].notna()) & (df['time_dt'].dt.month == month)
        df_cleaned = df[mask].copy()

        # Prep Final DataFrame
        df_cleaned['date_partition'] = df_cleaned['time_dt'].dt.date.astype(str) # String format for partitioning
        df_cleaned['time'] = df_cleaned['time_str'].astype(str).str.strip()
        final_df = df_cleaned[['time', 'value', 'prediction', '´site', 'measurement', 'unit', 'date_partition']]

        # 4. Write to Silver with Hive Partitioning
        if not final_df.empty:
            target_dir = f"{SILVER_BASE}/{month_str}"
            
            # Using partition_cols creates daily subfolders
            # storage_options is required here for the pyarrow engine
            final_df.to_parquet(
                target_dir,
                engine='pyarrow',
                index=False,
                partition_cols=['date_partition'],
                storage_options={"token": SERVICE_ACCOUNT_KEY}
            )
            logging.info(f"Month {month_str}: Successfully written as daily partitions.")
        else:
            logging.info(f"Month {month_str}: No valid data.")

    except Exception as e:
        logging.error(f"Failed to process Month {month_str}: {e}")
        
logging.info("--- Silver Layer Processing Complete ---")