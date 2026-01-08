# How to Run AQI Insight Dashboard

## Quick Start (Recommended)

### Option 1: Using PowerShell Script (Windows)
```powershell
cd aqi_dashboard
.\scripts\run.ps1
```

This script will:
1. Check if database exists, if not, ingest data
2. Start the FastAPI backend on port 8000
3. Start the Streamlit dashboard on port 8501

### Option 2: Manual Setup (Step by Step)

#### Step 1: Install Dependencies
```bash
cd aqi_dashboard
pip install -r requirements.txt
```

#### Step 2: Ingest Data (First time only)
```bash
python scripts/ingest_data.py
```

#### Step 3: Train Models (First time only)
```bash
python models/train_arima.py
python models/train_lstm.py
```

#### Step 4: Start Backend API (Terminal 1)
```bash
cd aqi_dashboard
python -m uvicorn app.main:app --reload --port 8000
```

#### Step 5: Start Dashboard (Terminal 2)
```bash
cd aqi_dashboard
streamlit run app/dashboard.py
```

## Access the Dashboard

Once running, open your browser and go to:
- **Dashboard**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

## Troubleshooting

### Backend not starting?
- Make sure port 8000 is not in use
- Check if database exists: `aqi_dashboard/database/aqi.db`

### Dashboard shows "Backend API not reachable"?
- Ensure the FastAPI backend is running on port 8000
- Check the terminal for any error messages

### No data showing?
- Run `python scripts/ingest_data.py` to populate the database
- Wait a few seconds for data ingestion to complete

## Notes
- The backend must be running before the dashboard can fetch data
- First run may take longer as it downloads and processes data
- Models need to be trained before forecasts will work

