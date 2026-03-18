import pandas as pd
import gcsfs
import os

# 1. Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"
BUCKET = "data-cycle-lake"
BRONZE_BASE = f"gs://{BUCKET}/raw/bellevuebooking/csv"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanbellevuebooking"

french_months = {
    'janv.': 'Jan', 'févr.': 'Feb', 'mars': 'Mar', 'avr.': 'Apr',
    'mai': 'May', 'juin': 'Jun', 'juil.': 'Jul', 'août': 'Aug',
    'sept.': 'Sep', 'oct.': 'Oct', 'nov.': 'Nov', 'déc.': 'Dec'
}

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
            continue
        
        print(f"--- Processing Month {month_str} ---")

        df_list = []
        for f in files:
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            with fs.open(full_path, mode='rb') as open_file:
                # Force Tab separator but use utf-8-sig to handle Byte Order Marks (BOM)
                # which often causes headers to be misread in Windows environments.
                chunk = pd.read_csv(
                    open_file, 
                    sep='\t', 
                    engine='python',
                    encoding='utf-8-sig', 
                    encoding_errors='replace',
                    on_bad_lines='skip'
                )
                
                # Clean up columns: strip whitespace and remove any quotes wrapping names
                chunk.columns = [str(c).strip().replace('"', '') for c in chunk.columns]
                df_list.append(chunk)
        
        if not df_list:
            continue
            
        df = pd.concat(df_list, ignore_index=True)

        # 2. Rename Columns
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

        # Check for column existence after cleaning
        if 'raw_date' not in df.columns:
            print(f"  ! Error: 'Date' column not found. Headers found: {df.columns.tolist()[:3]}...")
            continue

        # 3. Handle Placeholders
        cols_to_fill = ['room_id', 'instructor', 'department', 'activity_type']
        for col in cols_to_fill:
            if col in df.columns:
                df[col] = df[col].fillna("EMPTY")

        # 4. Date Transformation
        df['raw_date'] = df['raw_date'].astype(str).str.strip()
        for fr, en in french_months.items():
            df['raw_date'] = df['raw_date'].str.replace(fr, en, regex=False)
        
        df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d %b %Y', errors='coerce')

        # Use 1900-01-01 for invalid dates
        DATE_PLACEHOLDER = pd.Timestamp('1900-01-01')
        df['date_dt'] = df['date_dt'].fillna(DATE_PLACEHOLDER)
        df['date'] = df['date_dt'].dt.date.astype(str)

        # 5. Final Write
        cols_to_keep = ['date', 'room_id', 'start_time', 'end_time', 'reservation_id', 'activity_type', 'instructor', 'department']
        existing_cols = [c for c in cols_to_keep if c in df.columns]
        final_df = df[existing_cols].copy()

        if not final_df.empty:
            target_dir = f"{SILVER_BASE}/{month_str}"
            final_df.to_parquet(
                target_dir,
                engine='pyarrow',
                index=False,
                partition_cols=['date'],
                storage_options={"token": SERVICE_ACCOUNT_KEY}
            )
            print(f"  + Month {month_str} processed successfully.")
            
    except Exception as e:
        print(f"  !! Fatal Error in Month {month_str}: {e}")

print("\n--- Process Complete ---")