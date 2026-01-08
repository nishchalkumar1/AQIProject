
Write-Host "Starting AQI Insight Dashboard..."

# Verify Database
if (-not (Test-Path "database/aqi.db")) {
    Write-Host "Database not found. Running Ingestion..."
    python scripts/ingest_data.py
    python models/train_arima.py
    python models/train_lstm.py
}

# Start Backend
Write-Host "Starting FastAPI Backend..."
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --reload --port 8000" -NoNewWindow
Start-Sleep -Seconds 5

# Start Frontend
Write-Host "Starting Streamlit Dashboard..."
Start-Process -FilePath "python" -ArgumentList "-m streamlit run app/dashboard.py" -NoNewWindow

Write-Host "App launched. Visit http://localhost:8501"
