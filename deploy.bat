@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  DataCycleProject – Deployment Setup
echo ============================================================
echo.

:: ── 1. Verify prerequisites ──────────────────────────────────
echo [1/5] Checking prerequisites...

where py >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python (py launcher) not found. Install Python 3.11+ from python.org.
    pause & exit /b 1
)
echo  OK  Python found.

where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: gcloud CLI not found. Install the Google Cloud SDK.
    pause & exit /b 1
)
echo  OK  gcloud found.

where gsutil >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: gsutil not found. Install the Google Cloud SDK.
    pause & exit /b 1
)
echo  OK  gsutil found.

:: ── 2. Create .env from template if missing ──────────────────
echo.
echo [2/5] Checking .env configuration...

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo  CREATED .env from .env.example
    echo.
    echo  IMPORTANT: Open .env in a text editor and fill in all values
    echo  before re-running this script or starting the pipeline.
    echo.
    echo  Required values to fill in:
    echo    GCP_PROJECT, GCS_BUCKET, GOOGLE_APPLICATION_CREDENTIALS
    echo    ROOT_DIR, SFTP_PASS, KNIME_ID, KNIME_PASSWORD
    echo    KNIME_DEPLOYMENT_URL, and SMB drive letters.
    echo.
    pause
) else (
    echo  OK  .env already exists.
)

:: Load .env into the current batch session
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a"==" " set "%%a=%%b"
)

:: Validate required variables
set MISSING=0
for %%v in (GCP_PROJECT GCS_BUCKET GOOGLE_APPLICATION_CREDENTIALS ROOT_DIR SFTP_PASS KNIME_ID KNIME_PASSWORD) do (
    if "!%%v!"=="" (
        echo  ERROR: %%v is not set in .env
        set MISSING=1
    )
    if "!%%v!"=="your-gcp-project-id" set MISSING=1 & echo  ERROR: GCP_PROJECT still has placeholder value.
    if "!%%v!"=="your-gcs-bucket-name" set MISSING=1 & echo  ERROR: GCS_BUCKET still has placeholder value.
    if "!%%v!"=="your-sftp-password" set MISSING=1 & echo  ERROR: SFTP_PASS still has placeholder value.
    if "!%%v!"=="your-knime-app-id" set MISSING=1 & echo  ERROR: KNIME_ID still has placeholder value.
    if "!%%v!"=="your-knime-password" set MISSING=1 & echo  ERROR: KNIME_PASSWORD still has placeholder value.
)
if !MISSING! neq 0 (
    echo.
    echo  Please edit .env, then re-run deploy.bat
    pause & exit /b 1
)
echo  OK  All required variables are set.

:: Verify service account key file exists
if not exist "!GOOGLE_APPLICATION_CREDENTIALS!" (
    echo  ERROR: Service account key file not found:
    echo         !GOOGLE_APPLICATION_CREDENTIALS!
    echo  Copy the key JSON to that path and re-run.
    pause & exit /b 1
)
echo  OK  Service account key file found.

:: ── 3. Install Python dependencies ───────────────────────────
echo.
echo [3/5] Installing Python dependencies...

py -m pip install --upgrade pip --quiet
py -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  ERROR: Failed to install root requirements.
    pause & exit /b 1
)
echo  OK  Root requirements installed.

py -m pip install -r gold-layer-etl\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  ERROR: Failed to install gold-layer-etl requirements.
    pause & exit /b 1
)
echo  OK  gold-layer-etl requirements installed.

:: ── 4. Register Windows Task Scheduler ───────────────────────
echo.
echo [4/5] Registering Windows Task Scheduler task...

set TASK_NAME=DataCycleProject-Manager
set TASK_CMD="%~dp0start_manager.bat"

:: Delete existing task silently before re-creating (idempotent)
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "%TASK_CMD%" ^
  /sc DAILY ^
  /st 08:50 ^
  /ru "SYSTEM" ^
  /rl HIGHEST ^
  /f >nul

if %errorlevel% neq 0 (
    echo  WARNING: Could not register scheduled task automatically.
    echo  Manually create a task that runs: %TASK_CMD%
    echo  Schedule: Daily at 08:50, run as SYSTEM with highest privileges.
) else (
    echo  OK  Scheduled task '%TASK_NAME%' registered (daily at 08:50).
)

:: ── 5. Smoke test ─────────────────────────────────────────────
echo.
echo [5/5] Running smoke test (gcloud auth check)...

gcloud auth application-default print-access-token >nul 2>&1
if %errorlevel% neq 0 (
    echo  WARNING: Application Default Credentials not found.
    echo  Run: gcloud auth application-default login
    echo  Or ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly.
) else (
    echo  OK  GCP credentials are valid.
)

:: ── Done ──────────────────────────────────────────────────────
echo.
echo ============================================================
echo  Deployment setup complete.
echo  Start the listener manually with: start_manager.bat
echo  Or wait for the scheduled task to trigger at 08:50.
echo ============================================================
echo.
pause
endlocal
