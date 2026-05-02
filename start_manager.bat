@echo off
cd /d "%~dp0"

:: Load all variables from .env into this session
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a"==" " set "%%a=%%b"
)

echo Starting VM Listener... >> listener_log.txt
py manager.py >> listener_log.txt 2>&1
