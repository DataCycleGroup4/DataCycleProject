import pandas as pd
import gcsfs
import os

# 1. Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"

BUCKET = "data-cycle-lake"
BRONZE_BASE = f"gs://{BUCKET}/raw/bellevuebooking/csv"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanbellevuebooking"

# Mapping French months to English for Python's datetime parser
french_months = {
    'janv.': 'Jan', 'févr.': 'Feb', 'mars': 'Mar', 'avr.': 'Apr',
    'mai': 'May', 'juin': 'Jun', 'juil.': 'Jul', 'août': 'Aug',
    'sept.': 'Sep', 'oct.': 'Oct', 'nov.': 'Nov', 'déc.': 'Dec'
}

# Initialize Google Cloud Storage FileSystem
try:
    fs = gcsfs.GCSFileSystem(token=SERVICE_ACCOUNT_KEY)
    print("Authenticated successfully.")
except Exception as e:
    print(f"Auth failed: {e}")
    exit()

for month in range(1, 13):
    month_str = str(month).zfill(2)
    bronze_glob = f"{BRONZE_BASE}/{month_str}/*.csv*"
    
    try:
        # Find all files for the current month
        files = fs.glob(bronze_glob)
        if not files:
            print(f"  ! No files found in {bronze_glob}. Skipping.")
            continue
        
        print(f"  + Found {len(files)} files. Starting ingestion...")

        df_list = []
        for f in files:
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            with fs.open(full_path, mode='rb') as open_file:
                # Booking file uses Tabs ('\t') and UTF-8
                chunk = pd.read_csv(
                    open_file, 
                    sep='\t', 
                    engine='python',
                    encoding='utf-8', 
                    on_bad_lines='skip'
                )
                df_list.append(chunk)
        
        if not df_list:
            continue
            
        df = pd.concat(df_list, ignore_index=True)

        # 2. Cleaning & Renaming
        # Renaming columns from French to standard English technical names
        df = df.rename(columns={
            'Nom': 'room_id',
            'Date': 'raw_date',
            'Date de début': 'start_time',
            'Date de fin': 'end_time',
            'Rés.-no': 'reservation_id',
            'Activité': 'activity_type',
            'Professeur': 'instructor',
            'Division': 'department'
        })

        # 3. Date Transformation
        # 1. Convert to datetime, but keep the NaT (Not a Time) for now
        df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d %b %Y', errors='coerce')

        # 2. Define your placeholder
        DATE_PLACEHOLDER = pd.Timestamp('1900-01-01')
        STRING_PLACEHOLDER = "EMPTY"

        # 3. Fill the NaNs/NaTs before partitioning
        df['date_dt'] = df['date_dt'].fillna(DATE_PLACEHOLDER)

        # 4. Fill other categorical columns with "UNKNOWN"
        cols_to_fill = ['room_id', 'instructor', 'department']
        df[cols_to_fill] = df[cols_to_fill].fillna(STRING_PLACEHOLDER)

        # 5. Partitioning Logic
        df['date'] = df['date_dt'].dt.date.astype(str)

        df_cleaned = df.copy() 

        # Select relevant columns for the Silver Layer
        cols_to_keep = ['date', 'room_id', 'start_time', 'end_time', 'reservation_id', 'activity_type', 'instructor', 'department']
        final_df = df_cleaned[cols_to_keep]

        # 4. Write to Silver Layer 
        if not final_df.empty:
            target_dir = f"{SILVER_BASE}/{month_str}"
            
            # Using 'date' as a partition column creates daily folders automatically
            final_df.to_parquet(
                target_dir,
                engine='pyarrow',
                index=False,
                partition_cols=['date'],
                storage_options={"token": SERVICE_ACCOUNT_KEY}
            )
            print(f"Month {month_str}: Successfully written as daily partitions.")
        else:
            print(f"Month {month_str}: No valid data.")
            
    except Exception as e:
        print(f"Error in Month {month_str}: {e}")

print("\n--- Booking Silver Layer ETL Complete ---")