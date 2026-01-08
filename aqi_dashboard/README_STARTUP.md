# VAYUTEL AQI DASHBOARD STARTUP GUIDE

## Quick Start Options

### Option 1: PowerShell (Recommended for Windows 10/11)
```powershell
cd aqi_dashboard
powershell -ExecutionPolicy Bypass -File start_dashboard.ps1
```

### Option 2: Command Prompt (Windows)
```cmd
cd aqi_dashboard
start_dashboard_cmd.bat
```

### Option 3: Linux/Mac
```bash
cd aqi_dashboard
./start_dashboard.sh
```

### Option 4: Manual Startup

#### Terminal 1 - Backend:
```bash
cd aqi_dashboard
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Dashboard (after backend starts):
```bash
cd aqi_dashboard  
streamlit run app/dashboard.py --server.port 8501
```

## Access URLs
- **Dashboard**: http://localhost:8501
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## What's Working
✅ Live AQI data from Open-Meteo
✅ 168-hour ARIMA forecasts  
✅ 7-day historical data
✅ Weather integration
✅ 87 Indian cities
✅ Map-based AQI queries

## Troubleshooting
- If backend fails: Check Python dependencies
- If dashboard can't connect: Wait 10 seconds after backend starts
- If ports busy: Change ports in startup scripts

## System Status
- ARIMA Models: 11 cities trained
- LSTM Model: Trained and loaded
- Database: Connected with real data
- API Server: Ready for connections