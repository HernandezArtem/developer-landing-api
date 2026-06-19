@echo off
cd /d "%~dp0"
echo Starting Developer Landing API...
.\venv_new\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
pause