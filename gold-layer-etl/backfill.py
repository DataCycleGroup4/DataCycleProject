import subprocess, sys, os, time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Adjust these to your desired backfill range
start_date = datetime(2023, 4, 26)
end_date   = datetime(2023, 4, 30)
# ---------------------

dates = []
current = start_date
while current <= end_date:
    dates.append(current.strftime("%Y-%m-%d"))
    current += timedelta(days=1)

print(f"=== BACKFILL: {len(dates)} dates generated automatically ===")

# CRITICAL: Initialize counters before the loop
success = 0
failed = []

# Get the directory where backfill.py is located to find main.py
script_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(script_dir, "main.py")

for i, run_date in enumerate(dates, 1):
    print(f"\n[{i}/{len(dates)}] Processing {run_date}...")
    
    # Set environment variables for the subprocess
    os.environ["RUN_DATE"] = run_date
    os.environ["GCP_PROJECT"] = "project-d31bc18d-8d9f-48db-a77"
    os.environ["GCS_BUCKET"] = "data-cycle-lake"
    os.environ["BQ_DATASET"] = "DataCycle_Warehouse"
    os.environ["BQ_LOCATION"] = "EU"
    
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