import pandas as pd
import gcsfs
import csv
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
        
        # Clear the target month directory once before starting the file loop
        target_month_dir = f"{SILVER_BASE}/{month_str}"
        if fs.exists(target_month_dir):
            fs.rm(target_month_dir, recursive=True)

        for f in files:
            # Extract filename without extension (e.g., RoomAllocations_20230304)
            file_name = f.split('/')[-1].split('.')[0]
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            
            with fs.open(full_path, mode='rb') as open_file:
                df = pd.read_csv(
                    open_file, 
                    sep='\t', 
                    engine='python',
                    quoting=csv.QUOTE_NONE,
                    encoding='utf-8-sig', 
                    on_bad_lines='skip'
                )
            
            if df.empty:
                continue

            # 2. Cleanup Headers and Values
            df.columns = [c.strip().replace('"', '') for c in df.columns]
            
            # Vectorized cleaning for string columns only
            str_cols = df.select_dtypes(include=['object']).columns
            for col in str_cols:
                df[col] = df[col].astype(str).str.replace('"', '', regex=False).str.strip()

            # 3. Rename Columns
            df = df.rename(columns={
                'Nom': 'room_id',
                'Nom Entier': 'room_name',
                'Date': 'raw_date',
                'Date de début': 'start_time',
                'Date de fin': 'end_time',
                'Rés.-no': 'reservation_id',
                'Type de réservation': 'reservation_type',
                'Codes': 'reservation_code',
                'Nom de l\'utilisateur': 'reserved_by',
                'Sigle de salle remplacée': 'alt_room_id',
                'Nom entier de la salle remplacée': 'alt_room_name',
                'Classe': 'class',
                'Activité': 'activity_type',
                'Professeur': 'instructor',
                'Division': 'department',
                'Poste de dépenses': 'expense_category',
                'Remarque': 'remarks',
                'Annotation': 'comments'
            })

            # 4. Handle Placeholders
            cols_to_fill = [
                'room_id', 'instructor', 'department', 'activity_type', 
                'reservation_type', 'reservation_code', 'reserved_by', 
                'alt_room_id', 'class', 'expense_category', 'remarks', 'comments'
            ]
            for col in cols_to_fill:
                if col in df.columns:
                    df[col] = df[col].replace(['nan', 'None', ''], "EMPTY").fillna("EMPTY")

            # 5. Date Transformation
            if 'raw_date' in df.columns:
                # Efficient replacement of all months at once
                for fr, en in french_months.items():
                    df['raw_date'] = df['raw_date'].str.replace(fr, en, regex=False)
                
                df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d %b %Y', errors='coerce')
                df['date_dt'] = df['date_dt'].fillna(pd.Timestamp('1900-01-01'))
                df['date'] = df['date_dt'].dt.date.astype(str)

            # 6. Select Columns and Write
            cols_to_keep = [
                'date', 'room_id', 'start_time', 'end_time', 'reservation_id', 
                'reservation_type', 'reservation_code', 'reserved_by', 'alt_room_id', 
                'activity_type', 'instructor', 'department', 'class', 
                'expense_category', 'remarks', 'comments'
            ]
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            final_df = df[existing_cols].copy()

            # Save as a single Parquet file (No partitioning by date folder)
            target_file_path = f"{target_month_dir}/{file_name}.parquet"
            
            final_df.to_parquet(
                target_file_path,
                engine='pyarrow',
                index=False,
                storage_options={"token": SERVICE_ACCOUNT_KEY}
            )
            print(f"  + Processed: {file_name}.parquet")
            
    except Exception as e:
        print(f"  !! Fatal Error in Month {month_str}: {e}")

print("\n--- Process Complete ---")