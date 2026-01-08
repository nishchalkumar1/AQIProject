@echo off
echo ========================================
echo   Database Reset Tool
echo ========================================
echo.
echo This will:
echo 1. Backup the current database (if exists)
echo 2. Delete the corrupted database
echo 3. Create a fresh database
echo 4. Run data ingestion
echo.
echo WARNING: This will delete all existing data!
echo.
pause

cd /d %~dp0\..

echo.
echo [1/4] Fixing database...
python scripts\fix_database.py

echo.
echo [2/4] Ingesting data...
python scripts\ingest_data.py

echo.
echo [3/4] Training ARIMA model...
python models\train_arima.py

echo.
echo [4/4] Training LSTM model...
python models\train_lstm.py

echo.
echo ========================================
echo   Database reset complete!
echo ========================================
echo.
pause

