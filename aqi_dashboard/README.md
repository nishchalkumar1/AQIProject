
# Cloud-based AQI Insight Dashboard

A Single-student project to monitor, analyze, and forecast Air Quality (AQI) for Delhi using real historical data and predictive modeling.

## Project Structure
```
aqi_dashboard/
├── data/           # Data storage (Raw & Cleaned in DB)
├── database/       # SQLite database (aqi.db)
├── models/         # Training scripts & Saved models (ARIMA/LSTM)
├── app/            # Application Code
│   ├── main.py     # FastAPI Backend
│   └── dashboard.py# Streamlit Frontend
├── scripts/        # Utility scripts (Ingestion)
└── requirements.txt
```

## Setup & Run

### Prerequisites
- Python 3.8+
- Files in `requirements.txt` installed.

### Installation
```bash
pip install -r requirements.txt
```

### Data Pipeline
1. Ingest Data (Downloads from GitHub, cleans, and loads to DB):
   ```bash
   python scripts/ingest_data.py
   ```
2. Train Models:
   ```bash
   python models/train_arima.py
   python models/train_lstm.py
   ```

### Running the Application
You can run the full stack using the helper script:
```powershell
./scripts/run.ps1
```

Or manually:
1. Start Backend (Terminal 1):
   ```bash
   uvicorn app.main:app --reload
   ```
2. Start Frontend (Terminal 2):
   ```bash
   streamlit run app/dashboard.py
   ```

## Architecture
- **Data Source**: Historical hourly AQI data for Delhi (Source: GitHub/Real-time APIs).
- **Backend**: FastAPI serves REST endpoints for live data, history, and forecasts.
- **Database**: SQLite stores raw PM2.5 readings and computed AQI.
- **ML Engine**: 
  - **ARIMA**: Statistical baseline for time-series forecasting.
  - **LSTM**: Deep learning model for capturing complex non-linear patterns.
- **Frontend**: Streamlit dashboard with Plotly charts for interactive visualization.

## Models
- **ARIMA (5,1,0)**: Used for short-term forecasting.
- **LSTM (24h Window)**: User for capturing daily patterns and spikes.

## Health Impact
AQI categories (Good to Severe) are mapped to specific health advisories based on CPCB standards.

## Limitations
- Currently limited to Delhi (Data availability).
- Forecast accuracy depends on historical patterns; extreme events (e.g. crop burning) need external features.
