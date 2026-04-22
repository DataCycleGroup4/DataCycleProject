@echo off
cd /d "C:\Users\Administrator\Desktop\DataCycleProject"
set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json
echo Starting VM Listener... >> listener_log.txt
py manager.py >> listener_log.txt 2>&1