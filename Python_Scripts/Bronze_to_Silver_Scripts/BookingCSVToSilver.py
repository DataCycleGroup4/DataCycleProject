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
        files = fs.glob(bronze_glob)
        if not files:
            print(f"  ! No files found in {bronze_glob}. Skipping.")
            continue
        
        print(f"  + Month {month_str}: Processing {len(files)} files...")

        df_list = []
        for f in files:
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            with fs.open(full_path, mode='rb') as open_file:
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

        # 3. Date Transformation & Imputation
        # Ensure raw_date is a string and handle existing NaNs
        df['raw_date'] = df['raw_date'].astype(str).replace('nan', '')

        for fr, en in french_months.items():
            df['raw_date'] = df['raw_date'].str.replace(fr, en, regex=False)
        
        # Convert to datetime (Now it will recognize "Mar", "Apr", etc.)
        df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d %b %Y', errors='coerce')

        # Define placeholders
        DATE_PLACEHOLDER = pd.Timestamp('1900-01-01')
        STRING_PLACEHOLDER = "EMPTY"

        df['date_dt'] = df['date_dt'].fillna(DATE_PLACEHOLDER)

        # Fill other categorical columns
        cols_to_fill = ['room_id', 'instructor', 'department', 'activity_type']
        df[cols_to_fill] = df[cols_to_fill].fillna(STRING_PLACEHOLDER)

        # Create 'date' string for partitioning
        df['date'] = df['date_dt'].dt.date.astype(str)

        # Select relevant columns
        cols_to_keep = ['date', 'room_id', 'start_time', 'end_time', 'reservation_id', 'activity_type', 'instructor', 'department']
        final_df = df[cols_to_keep].copy()

        # 4. Write to Silver Layer 
        if not final_df.empty:
            target_dir = f"{SILVER_BASE}/{month_str}"
            
            final_df.to_parquet(
                target_dir,
                engine='pyarrow',
                index=False,
                partition_cols=['date'],
                storage_options={"token": SERVICE_ACCOUNT_KEY}
            )
            print(f"  -> Successfully written partitions for Month {month_str}.")
        else:
            print(f"  ! Month {month_str}: No data to write.")
            
    except Exception as e:
        print(f"Error in Month {month_str}: {e}")

print("\n--- Booking Silver Layer ETL Complete ---")