# POWERSTART - VAYUTEL AQI DASHBOARD

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "    VAYUTEL AQI DASHBOARD" -ForegroundColor Cyan  
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Dashboard fixes applied:" -ForegroundColor Green
Write-Host "  1. Plotly timestamp compatibility" -ForegroundColor White
Write-Host "  2. Missing 'city' column handling" -ForegroundColor White
Write-Host "  3. Deprecated parameter updates" -ForegroundColor White
Write-Host ""

Write-Host "Starting AQI Backend Server..." -ForegroundColor Yellow
Write-Host ""

# Start backend in background using PowerShell Start-Process
$backendArgs = @(
    "-NoExit",
    "-Command", 
    "cd '$PSScriptRoot'; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)
Start-Process -FilePath "powershell" -ArgumentList $backendArgs -WindowStyle Minimized

Write-Host ""
Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "Starting Streamlit Dashboard..." -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard will open at: http://localhost:8501" -ForegroundColor White
Write-Host "API will be running at: http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C in PowerShell windows to stop servers" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Cyan

# Start dashboard
streamlit run app/dashboard.py --server.port 8501 --server.headless false