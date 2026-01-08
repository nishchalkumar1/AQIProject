@echo off
echo ====================================
echo     VAYUTEL AQI DASHBOARD
echo ====================================
echo.
echo Dashboard fixes applied:
echo  1. Plotly timestamp compatibility
echo  2. Missing 'city' column handling  
echo  3. Deprecated parameter updates
echo.
echo Starting AQI Backend Server...
echo.

REM Start backend in background using Command Prompt
start /min cmd /c "cd /d %~dp0 && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo Waiting for backend to start...
timeout /t 8 /nobreak >nul

echo.
echo Starting Streamlit Dashboard...
echo.
echo Dashboard will open at: http://localhost:8501
echo API will be running at: http://localhost:8000
echo.
echo Press Ctrl+C in each window to stop the servers
echo ====================================

REM Start dashboard
streamlit run app/dashboard.py --server.port 8501 --server.headless false

pause