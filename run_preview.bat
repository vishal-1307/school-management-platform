@echo off
echo ====================================================
echo   Knowledge Academy Platform Preview Launcher
echo ====================================================

:: Start Backend
echo Starting Backend (FastAPI)...
start cmd /k "cd backend && python seed.py && python -m uvicorn app.main:app --port 8000 --reload"

:: Start Frontend
echo Starting Frontend (Astro)...
start cmd /k "cd /d "%~dp0frontend" && npm install && npm run dev"

echo Both servers are starting in separate windows!
echo - API Docs: http://127.0.0.1:8000/docs
echo - Public Website: http://localhost:4321
echo ====================================================
pause
