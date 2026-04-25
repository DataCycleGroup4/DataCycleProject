import pandas as pd
import gcsfs
import csv

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

# 2. Find the single most recent file across all month folders
all_files = fs.glob(f"{BRONZE_BASE}/**/*.csv*")
if not all_files:
    print("No files found in bronze layer.")
    exit()

latest_file = sorted(all_files)[-1]
print(f"Using latest file: {latest_file}")

# 3. Read it
full_path = latest_file if latest_file.startswith('gs://') else f"gs://{latest_file}"
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
    print("File is empty.")
    exit()

# 4. Cleanup Headers and Values
df.columns = [c.strip().replace('"', '') for c in df.columns]
str_cols = df.select_dtypes(include=['object']).columns
for col in str_cols:
    df[col] = df[col].astype(str).str.replace('"', '', regex=False).str.strip()

# 5. Rename Columns
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

# 6. Handle Placeholders
cols_to_fill = [
    'room_id', 'instructor', 'department', 'activity_type',
    'reservation_type', 'reservation_code', 'reserved_by',
    'alt_room_id', 'class', 'expense_category', 'remarks', 'comments'
]
for col in cols_to_fill:
    if col in df.columns:
        df[col] = df[col].replace(['nan', 'None', ''], "EMPTY").fillna("EMPTY")

# 7. Date Transformation
if 'raw_date' in df.columns:
    for fr, en in french_months.items():
        df['raw_date'] = df['raw_date'].str.replace(fr, en, regex=False)
    df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d %b %Y', errors='coerce')
    df['date_dt'] = df['date_dt'].fillna(pd.Timestamp('1900-01-01'))
    df['date'] = df['date_dt'].dt.date.astype(str)

# 8. Select Columns
cols_to_keep = [
    'date', 'room_id', 'start_time', 'end_time', 'reservation_id',
    'reservation_type', 'reservation_code', 'reserved_by', 'alt_room_id',
    'activity_type', 'instructor', 'department', 'class',
    'expense_category', 'remarks', 'comments'
]
existing_cols = [c for c in cols_to_keep if c in df.columns]
final_df = df[existing_cols].copy()

# 9. Clear entire silver booking layer and rewrite
if fs.exists(SILVER_BASE):
    print("Clearing existing silver layer...")
    fs.rm(SILVER_BASE, recursive=True)

# Partition by month for efficient querying
final_df['month'] = pd.to_datetime(final_df['date']).dt.strftime('%m')
for month_str, month_df in final_df.groupby('month'):
    month_df = month_df.drop(columns=['month'])
    target_file = f"{SILVER_BASE}/{month_str}/RoomAllocations_latest.parquet"
    month_df.to_parquet(
        target_file,
        engine='pyarrow',
        index=False,
        storage_options={"token": SERVICE_ACCOUNT_KEY}
    )
    print(f"  + Written: {month_str}/RoomAllocations_latest.parquet ({len(month_df)} rows)")

print("\n--- Silver Layer Complete ---")