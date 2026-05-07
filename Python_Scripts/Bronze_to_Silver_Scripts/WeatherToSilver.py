import os
import pandas as pd
import gcsfs
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# 1. Configuration
SERVICE_ACCOUNT_KEY = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
BUCKET = os.environ["GCS_BUCKET"]
BRONZE_BASE = f"gs://{BUCKET}/raw/weather"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanweather"

# Initialize GCS
try:
    fs = gcsfs.GCSFileSystem(token=SERVICE_ACCOUNT_KEY)
    print("------------------------------------------")
    print("Authenticated successfully with GCS.")
    print("------------------------------------------")
except Exception as e:
    print(f"Auth failed: {e}")
    exit()

for month in range(1, 13):
    month_str = str(month).zfill(2)
    bronze_glob = f"{BRONZE_BASE}/{month_str}/*.csv*"
    
    print(f"\n[Month {month_str}] Searching for files...")
    
    try:
        files = fs.glob(bronze_glob)
        if not files:
            print(f" No files found in {bronze_glob}. Skipping.")
            continue
        
        print(f"  + Found {len(files)} files. Starting ingestion...")

        df_list = []
        for i, f in enumerate(files):
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            try:
                with fs.open(full_path, mode='rb') as open_file:
                    # Using 'utf-8-sig' for safety and default engine for speed
                    chunk = pd.read_csv(
                        open_file, 
                        sep=',', 
                        encoding='utf-8-sig', 
                        on_bad_lines='skip',
                        low_memory=False
                    )
                    if not chunk.empty:
                        df_list.append(chunk)
                
                # Progress logging every 10 files
                if (i + 1) % 10 == 0:
                    print(f"    - Processed {i + 1}/{len(files)} files...")
                    
            except Exception as read_e:
                print(f"  Error reading {f}: {read_e}")
        
        if not df_list:
            print(f" All files in Month {month_str} were empty or unreadable.")
            continue
            
        df = pd.concat(df_list, ignore_index=True)
        print(f"  + Merged {len(df)} total raw rows. Starting cleaning...")

        # 3. Transform & Clean
        df = df.rename(columns={
            df.columns[0]: 'time_raw',
            df.columns[1]: 'value',
            df.columns[2]: 'prediction',
            df.columns[3]: 'site',
            df.columns[4]: 'measurement',
            df.columns[5]: 'unit'
        })

        df['time_dt'] = pd.to_datetime(df['time_raw'], errors='coerce', utc=True)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['prediction'] = pd.to_numeric(df['prediction'], errors='coerce')

        mask = (df['time_dt'].notna()) & (df['value'] != -99999.0) & (df['time_dt'].dt.month == month)
        df_cleaned = df[mask].copy()

        if df_cleaned.empty:
            print(f"Month {month_str}: No valid data survived the filters.")
            continue

        df_cleaned['date_partition'] = df_cleaned['time_dt'].dt.date.astype(str)
        df_cleaned['time'] = df_cleaned['time_dt'].dt.strftime('%H:%M:%S')
        
        final_df = df_cleaned[['date_partition', 'time', 'value', 'prediction', 'site', 'measurement', 'unit']]

        # 4. Write to Silver
        target_dir = f"{SILVER_BASE}/{month_str}"
        print(f"  + Writing {len(final_df)} cleaned rows to Parquet: {target_dir}")

                    # added code to clean out previous files from directory
        if fs.exists(target_dir):
            print(f"Month {month_str}: Existing data found. Deleting to prevent duplicates...")
                # recursive=True is vital to remove the directory and all sub-partitions
            fs.rm(target_dir, recursive=True)
        
        final_df.to_parquet(
            target_dir,
            engine='pyarrow',
            index=False,
            partition_cols=['date_partition'],
            storage_options={"token": SERVICE_ACCOUNT_KEY}
        )
        print(f"Month {month_str} cwoomplete.")

    except Exception as e:
        print(f"Critical Error in Month {month_str}: {e}")

print("\n--- Silver Layer Process Complete ---")
