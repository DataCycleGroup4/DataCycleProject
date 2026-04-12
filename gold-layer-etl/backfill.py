import subprocess, sys, os, time

dates_file = "/tmp/valid_dates.txt"
with open(dates_file) as f:
    dates = [d.strip() for d in f if d.strip()]

print(f"=== BACKFILL: {len(dates)} dates to process ===")
success = 0
failed = []

for i, run_date in enumerate(dates, 1):
    print(f"\n[{i}/{len(dates)}] Processing {run_date}...")
    os.environ["RUN_DATE"] = run_date
    os.environ["GCP_PROJECT"] = "project-d31bc18d-8d9f-48db-a77"
    os.environ["GCS_BUCKET"] = "data-cycle-lake"
    os.environ["BQ_DATASET"] = "DataCycle_Warehouse"
    os.environ["BQ_LOCATION"] = "EU"
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True, text=True, timeout=3600
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            success += 1
            print(f"  OK ({elapsed:.1f}s)")
        else:
            failed.append(run_date)
            print(f"  FAILED ({elapsed:.1f}s): {result.stderr[-300:]}")
    except Exception as e:
        failed.append(run_date)
        print(f"  ERROR: {e}")

print(f"\n=== BACKFILL COMPLETE ===")
print(f"Success: {success}")
print(f"Failed: {len(failed)}")
if failed:
    print(f"Failed dates: {failed}")
