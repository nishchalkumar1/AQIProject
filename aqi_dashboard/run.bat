@echo off
echo ========================================
echo   AQI Insight Dashboard Launcher
echo ========================================
echo.

cd /d %~dp0

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [2/4] Checking dependencies...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo [3/4] Checking database...
if not exist "database\aqi.db" (
    echo Database not found. Running data ingestion...
    python scripts\ingest_data.py
    echo.
    echo Training models (this may take a few minutes)...
    python models\train_arima.py
    python models\train_lstm.py
)

echo [4/4] Starting services...
echo.
echo Starting FastAPI Backend on http://localhost:8000
start "AQI Backend" cmd /k "python -m uvicorn app.main:app --reload --port 8000"

timeout /t 5 /nobreak >nul

echo Starting Streamlit Dashboard on http://localhost:8501
start "AQI Dashboard" cmd /k "streamlit run app\dashboard.py"

echo.
echo ========================================
echo   Dashboard is starting!
echo   Open http://localhost:8501 in your browser
echo ========================================
echo.
echo Press any key to exit this window (services will keep running)...
pause >nul

