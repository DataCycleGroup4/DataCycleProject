import subprocess, sys, os, time
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# --- CONFIGURATION ---
# Calculate current dates
today = datetime.now()
tomorrow = today + timedelta(days=1)
day_after = today + timedelta(days=2)

# Helper to safely replace the year (handles Feb 29th leap year edge cases)
def safe_replace_year(dt, target_year):
    try:
        return dt.replace(year=target_year)
    except ValueError:
        # Fallback to Feb 28th if trying to push Feb 29th into a non-leap year
        return dt.replace(year=target_year, day=28)

# Dynamically generate start and end dates for 2023
start_date = safe_replace_year(tomorrow, 2023)
end_date = safe_replace_year(day_after, 2023)
# ---------------------

dates = []
current = start_date
while current <= end_date:
    dates.append(current.strftime("%Y-%m-%d"))
    current += timedelta(days=1)

print(f"=== BACKFILL: {len(dates)} dates generated automatically ===")
print(f"Target Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

# CRITICAL: Initialize counters before the loop
success = 0
failed = []

# Get the directory where backfill.py is located to find main.py
script_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(script_dir, "main.py")

for i, run_date in enumerate(dates, 1):
    print(f"\n[{i}/{len(dates)}] Processing {run_date}...")
    
    # RUN_DATE changes each iteration; all other vars come from .env
    os.environ["RUN_DATE"] = run_date
    
    start = time.time()
    try:
        # Run main.py
        result = subprocess.run(
            [sys.executable, main_script],
            capture_output=True, text=True, timeout=3600
        )
        
        elapsed = time.time() - start
        if result.returncode == 0:
            success += 1
            print(f"  OK ({elapsed:.1f}s)")
        else:
            failed.append(run_date)
            # Print the last bit of the error if it fails
            error_msg = result.stderr[-500:] if result.stderr else "No stderr output"
            print(f"  FAILED ({elapsed:.1f}s): {error_msg}")
            
    except Exception as e:
        failed.append(run_date)
        print(f"  ERROR: {e}")

print(f"\n=== BACKFILL COMPLETE ===")
print(f"Success: {success}")
print(f"Failed: {len(failed)}")
if failed:
    print(f"Failed dates: {failed}")