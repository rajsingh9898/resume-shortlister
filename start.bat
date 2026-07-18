@echo off
echo =============================================================
echo               TalentAI - Resume Shortlister                  
echo =============================================================
echo.
echo [1/2] Opening Web Dashboard in default browser...
start http://127.0.0.1:8000

echo [2/2] Launching Python FastAPI Server...
echo.
cd backend
python main.py
pause