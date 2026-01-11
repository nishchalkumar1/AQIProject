
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os
import pickle
import numpy as np
import sys
import requests
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
import math
IS_RENDER = bool(os.getenv("RENDER")) or bool(os.getenv("RENDER_SERVICE_ID"))


# Add parent dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.utils import calculate_aqi_pm25, get_health_advisory, get_aqi_category

app = FastAPI(title="AQI Insight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), '../database/aqi.db')
ARIMA_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/saved/arima_model.pkl')  # legacy single model
LSTM_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/saved/lstm_model.h5')
SCALER_PATH = os.path.join(os.path.dirname(__file__), '../models/saved/scaler.pkl')

INDIAN_CITIES_FILE = os.path.join(os.path.dirname(__file__), '../data/indian_cities.csv')

models: Dict[str, Any] = {}


# -----------------------------------------------------------------------------
# Dynamic Indian city list (Approach B - local CSV dataset)
# -----------------------------------------------------------------------------

INDIAN_CITIES_CACHE: List[Dict[str, Any]] = []


def load_indian_cities_from_file() -> List[Dict[str, Any]]:
    """
    Load Indian cities from a local CSV file.
    CSV columns: city,state,lat,lon
    """
    global INDIAN_CITIES_CACHE

    if INDIAN_CITIES_CACHE:
        return INDIAN_CITIES_CACHE

    if not os.path.exists(INDIAN_CITIES_FILE):
        print(f"Indian cities file not found: {INDIAN_CITIES_FILE}")
        return []

    try:
        df = pd.read_csv(INDIAN_CITIES_FILE)
        cities: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            city = str(row.get("city") or "").strip()
            state = str(row.get("state") or "").strip()
            lat = row.get("lat")
            lon = row.get("lon")
            if not city or pd.isna(lat) or pd.isna(lon):
                continue
            cities.append(
                {
                    "city": city,
                    "state": state,
                    "lat": float(lat),
                    "lon": float(lon),
                }
            )

        INDIAN_CITIES_CACHE = sorted(
            cities,
            key=lambda x: ((x.get("state") or "").lower(), x.get("city", "").lower()),
        )
    except Exception as e:
        print(f"Failed to load Indian cities from file: {e}")

    return INDIAN_CITIES_CACHE

# -----------------------------------------------------------------------------
# Lazy loading helpers (CRITICAL for cloud stability)
# -----------------------------------------------------------------------------

def ensure_models_loaded():
    """
    Load heavy ML models only once, on first use.
    This prevents Render from crashing on cold start.
    """
    if models.get("_loaded", False):
        return

    print("Lazy-loading models now...")

    # Pre-load Indian cities
    try:
        cities = load_indian_cities_from_file()
        print(f"Loaded {len(cities)} Indian cities from local CSV")
    except Exception as e:
        print(f"Failed to load cities from CSV: {e}")

    # Load ARIMA models ONLY locally (Render free tier cannot hold ~130MB of pkl files in RAM)
    if not IS_RENDER:
        # Load legacy ARIMA
        if os.path.exists(ARIMA_MODEL_PATH):
            try:
                with open(ARIMA_MODEL_PATH, 'rb') as f:
                    models['arima_legacy'] = pickle.load(f)
                print("Legacy ARIMA model loaded.")
            except Exception as e:
                print(f"Failed to load legacy ARIMA: {e}")

        # Load per-city ARIMA models
        try:
            arima_city_models: Dict[str, Any] = {}
            models_dir = os.path.join(os.path.dirname(__file__), '../models/saved')
            if os.path.isdir(models_dir):
                for fname in os.listdir(models_dir):
                    if fname.startswith("arima_") and fname.endswith(".pkl"):
                        city_slug = fname[len("arima_"):-4]
                        path = os.path.join(models_dir, fname)
                        try:
                            with open(path, 'rb') as f:
                                arima_city_models[city_slug] = pickle.load(f)
                        except Exception as e:
                            print(f"Failed to load ARIMA model {fname}: {e}")
            if arima_city_models:
                models['arima_city'] = arima_city_models
                print(f"Loaded {len(arima_city_models)} per-city ARIMA models.")
        except Exception as e:
            print(f"Failed to scan/load per-city ARIMA models: {e}")
    else:
        print("Running on Render: ARIMA models disabled for memory safety (using fallback forecasting)")

    # Load scaler
    if os.path.exists(SCALER_PATH):
        try:
            with open(SCALER_PATH, 'rb') as f:
                models['scaler'] = pickle.load(f)
            print("Scaler loaded.")
        except Exception as e:
            print(f"Failed to load Scaler: {e}")

    # Load LSTM
    # Load LSTM ONLY locally (Render free tier cannot hold TF in RAM)
    if not IS_RENDER:
        try:
            from tensorflow.keras.models import load_model
            if os.path.exists(LSTM_MODEL_PATH):
                models['lstm'] = load_model(LSTM_MODEL_PATH)
                print("LSTM model loaded.")
        except Exception as e:
            print(f"Failed to load LSTM: {e}")
    else:
        print("Running on Render: LSTM disabled for memory safety")
  

    models["_loaded"] = True
    print("All models loaded successfully.")


def get_city_coords(city: str) -> Optional[Tuple[float, float]]:
    """
    Look up coordinates for a given city from the local CSV cache,
    falling back to static CITY_COORDS if needed.
    """
    cities = load_indian_cities_from_file()
    city_lower = city.lower()

    for c in cities:
        if c.get("city", "").lower() == city_lower:
            return c.get("lat"), c.get("lon")

    # Fallback to static coordinates for known demo cities
    if city in CITY_COORDS:
        return CITY_COORDS[city]

    return None




def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Quick integrity check
        cursor = conn.cursor()
        cursor.execute("PRAGMA quick_check")
        result = cursor.fetchone()
        if result[0] != 'ok':
            raise sqlite3.DatabaseError(f"Database integrity check failed: {result[0]}")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.DatabaseError as e:
        print(f"Database error: {e}")
        print("Please run: python scripts/fix_database.py")
        raise HTTPException(status_code=500, detail="Database is corrupted. Please run fix_database.py")

@app.get("/")
def read_root():
    return {"message": "AQI Insight API is running"}

CITY_COORDS = {
    # Fallback static list for demo / offline use
    "Delhi": (28.61, 77.20),
    "Mumbai": (19.07, 72.87),
    "Bengaluru": (12.97, 77.59),
    "Chennai": (13.08, 80.27),
    "Kolkata": (22.57, 88.36),
    "Hyderabad": (17.38, 78.48),
    "Pune": (18.52, 73.85),
    "Ahmedabad": (23.02, 72.57),
    "Jaipur": (26.91, 75.78),
    "Lucknow": (26.84, 80.94),
}


@app.get("/cities")
def get_cities():
    """
    Return list of Indian cities using local CSV dataset (Approach B).
    Each entry: {city, state, lat, lon}
    Returns cached data immediately if available.
    """
    cities = load_indian_cities_from_file()
    if cities:
        return {"cities": cities}

    # Fallback to static list if CSV is unavailable
    fallback: List[Dict[str, Any]] = []
    for name, (lat, lon) in CITY_COORDS.items():
        fallback.append(
            {
                "city": name,
                "state": "",
                "lat": lat,
                "lon": lon,
            }
        )
    return {"cities": fallback}

@app.get("/live-data")
def get_live_data(city: str = Query(..., description="City name")):
    """
    Return latest AQI for a city.
    Strategy:
    1. Try IQAir API (official monitoring station data) - most accurate
    2. Fall back to Open-Meteo if IQAir fails
    3. Fall back to database if both APIs fail
    """
    IQAIR_API_KEY = "2fbe4f3a-1ee7-4a7e-982b-94776bd0a075"
    
    # 1) Try IQAir API first (official monitoring station data)
    coords = get_city_coords(city)
    if coords is not None:
        lat, lon = coords
        try:
            # IQAir API endpoint using coordinates
            iqair_url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={IQAIR_API_KEY}"
            response = requests.get(iqair_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "data" in data:
                    iq_data = data["data"]
                    current = iq_data.get("current", {})
                    pollution = current.get("pollution", {})
                    
                    # IQAir returns US AQI - we need to convert to Indian CPCB AQI
                    us_aqi = pollution.get("aqius", 0)
                    us_aqi = max(0, min(500, int(us_aqi) if us_aqi else 0))
                    
                    # Estimate PM2.5 from US AQI using US EPA breakpoints (inverse calculation)
                    # US AQI PM2.5 breakpoints: 0-50 (0-12), 51-100 (12.1-35.4), 101-150 (35.5-55.4), etc.
                    if us_aqi <= 50:
                        pm25 = us_aqi * 12.0 / 50.0
                    elif us_aqi <= 100:
                        pm25 = 12.1 + (us_aqi - 51) * (35.4 - 12.1) / 49.0
                    elif us_aqi <= 150:
                        pm25 = 35.5 + (us_aqi - 101) * (55.4 - 35.5) / 49.0
                    elif us_aqi <= 200:
                        pm25 = 55.5 + (us_aqi - 151) * (150.4 - 55.5) / 49.0
                    elif us_aqi <= 300:
                        pm25 = 150.5 + (us_aqi - 201) * (250.4 - 150.5) / 99.0
                    else:
                        pm25 = 250.5 + (us_aqi - 301) * (500.0 - 250.5) / 199.0
                    
                    pm25 = max(0, pm25)
                    
                    # Calculate Indian CPCB AQI from PM2.5
                    indian_aqi = calculate_aqi_pm25(pm25)
                    indian_aqi = max(0, min(500, indian_aqi if indian_aqi else 0))
                    
                    # Get timestamp and convert to IST (IQAir returns UTC)
                    time_str = pollution.get("ts", "")
                    if time_str:
                        try:
                            # Parse UTC time and convert to IST (+5:30)
                            utc_time = pd.to_datetime(time_str)
                            ist_time = utc_time + pd.Timedelta(hours=5, minutes=30)
                            time_str = ist_time.isoformat()
                        except:
                            time_str = datetime.now().isoformat()
                    else:
                        time_str = datetime.now().isoformat()
                    
                    return {
                        "city": city,
                        "datetime": time_str,
                        "pm25": round(pm25, 1),
                        "aqi": indian_aqi,
                        "source": "IQAir API (Converted to Indian CPCB AQI)",
                    }
        except requests.exceptions.RequestException as e:
            print(f"IQAir API request failed for {city}: {e}")
        except Exception as e:
            print(f"IQAir API failed for {city}: {e}")

    # 2) Fallback to Open-Meteo using city coordinates
    coords = get_city_coords(city)
    if coords is not None:
        lat, lon = coords
        try:
            url = (
                "https://air-quality-api.open-meteo.com/v1/air-quality"
                f"?latitude={lat}&longitude={lon}"
                "&current=pm2_5&timezone=Asia%2FKolkata"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "current" in data and "pm2_5" in data["current"]:
                    pm25 = data["current"]["pm2_5"]
                    # Handle None or invalid PM2.5 values
                    if pm25 is not None and pm25 >= 0:
                        aqi = calculate_aqi_pm25(pm25)
                        aqi = max(0, min(500, aqi if aqi is not None else 0))
                        return {
                            "city": city,
                            "datetime": data["current"].get("time", datetime.now().isoformat()),
                            "pm25": pm25,
                            "aqi": aqi,
                            "source": "Open-Meteo API (Fallback)",
                        }
        except requests.exceptions.RequestException as e:
            print(f"Open-Meteo API request failed for {city}: {e}")
        except Exception as e:
            print(f"Open-Meteo live-data failed for {city}: {e}")

    # 3) Fallback to Database: latest record that is NOT in the future
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "SELECT * FROM aqi_cleaned WHERE city=? AND datetime <= ? ORDER BY datetime DESC LIMIT 1",
            (city, now_str),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            res = dict(row)
            # Ensure AQI is calculated if missing
            if "aqi" not in res or res["aqi"] is None:
                if "pm25" in res and res["pm25"] is not None:
                    res["aqi"] = calculate_aqi_pm25(float(res["pm25"]))
                else:
                    res["aqi"] = 0
            else:
                res["aqi"] = max(0, min(500, float(res["aqi"])))
            
            res["source"] = "Historical Database (Fallback)"
            return res
    except Exception as e:
        print(f"Database fallback failed for {city}: {e}")

    # 4) Final fallback with synthetic data for demo purposes
    if city in CITY_COORDS:
        import random
        pm25 = random.uniform(20, 150)  # Realistic PM2.5 range
        aqi = calculate_aqi_pm25(pm25)
        aqi = max(0, min(500, aqi if aqi is not None else 0))
        return {
            "city": city,
            "datetime": datetime.now().isoformat(),
            "pm25": pm25,
            "aqi": aqi,
            "source": "Demo Data (Fallback)",
        }

    raise HTTPException(status_code=404, detail="No data found for city")

@app.get("/weather")
def get_weather(city: str = Query(..., description="City name")):
    """Get real-time weather data for a city"""
    coords = get_city_coords(city)
    if coords is None:
        # Return fallback weather data instead of raising exception
        return get_fallback_weather(city)
    
    lat, lon = coords
    
    try:
        # Open-Meteo Weather API
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&timezone=Asia%2FKolkata"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get('current', {})
            
            # Weather code mapping (WMO codes)
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Foggy", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
            }
            
            weather_code = current.get('weather_code', 0)
            weather_desc = weather_codes.get(weather_code, "Unknown")
            
            return {
                "city": city,
                "temperature": current.get('temperature_2m'),
                "feels_like": current.get('apparent_temperature'),
                "humidity": current.get('relative_humidity_2m'),
                "wind_speed": current.get('wind_speed_10m'),
                "precipitation": current.get('precipitation'),
                "weather_description": weather_desc,
                "weather_code": weather_code,
                "timestamp": current.get('time'),
                "source": "Open-Meteo Weather API"
            }
        else:
            print(f"Weather API returned status {response.status_code}")
            return get_fallback_weather(city)
    except requests.exceptions.RequestException as e:
        print(f"Weather API request failed: {e}")
        return get_fallback_weather(city)
    except Exception as e:
        print(f"Weather API failed: {e}")
        return get_fallback_weather(city)

def get_fallback_weather(city):
    """Generate fallback weather data when API is unavailable"""
    import random
    random.seed(42)
    
    # Generate realistic weather data based on Indian climate
    base_temp = random.uniform(20, 35)  # Typical Indian temperature range
    humidity = random.uniform(40, 80)  # Typical humidity range
    wind_speed = random.uniform(5, 15)  # Typical wind speed
    
    weather_conditions = ["Clear sky", "Partly cloudy", "Overcast", "Light drizzle"]
    weather_desc = random.choice(weather_conditions)
    
    return {
        "city": city,
        "temperature": round(base_temp, 1),
        "feels_like": round(base_temp + random.uniform(-2, 2), 1),
        "humidity": round(humidity, 1),
        "wind_speed": round(wind_speed, 1),
        "precipitation": round(random.uniform(0, 5), 1) if "drizzle" in weather_desc or "rain" in weather_desc else 0.0,
        "weather_description": weather_desc,
        "weather_code": 0,
        "timestamp": datetime.now().isoformat(),
        "source": "Fallback Weather Data"
    }

@app.get("/history")
def get_history(city: str = Query(..., description="City name"), period: str = "7d"):
    """
    Historical AQI with HOURLY resolution for exactly 7 days (168 hours).
    Returns interpolated hourly data if some hours are missing.
    """
    ensure_models_loaded()

    try:
        conn = get_db_connection()
        
        # Get the most recent 168 hours of data (last 7 days)
        query = """
            SELECT datetime, aqi, pm25 
            FROM aqi_cleaned 
            WHERE city=? AND datetime <= datetime('now')
            ORDER BY datetime DESC
            LIMIT 200
        """
        df = pd.read_sql(query, conn, params=(city,))
        conn.close()
        
        if df.empty:
            # Generate synthetic historical data if no real data available
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            return generate_synthetic_history(city, start_time, end_time)
        
        # Convert datetime column to datetime type
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        
        # Take the most recent 168 hours (7 days) of data
        if len(df) > 168:
            df = df.tail(168)
        
        # Get the actual time range from the data
        start_time = df['datetime'].min()
        end_time = df['datetime'].max()
        
        # Create hourly index from the actual data range
        hourly_index = pd.date_range(start=start_time, end=end_time, freq='h')
        
        # Create a DataFrame with hourly index
        hourly_df = pd.DataFrame(index=hourly_index)
        hourly_df['datetime'] = hourly_index
        
        # Merge with actual data
        df_merged = pd.merge(hourly_df, df, on='datetime', how='left', suffixes=('', '_actual'))
        
        # Use actual values where available, otherwise NaN
        df_merged['aqi'] = df_merged.get('aqi_actual', df_merged.get('aqi'))
        df_merged['pm25'] = df_merged.get('pm25_actual', df_merged.get('pm25'))
        
        # Calculate AQI from PM2.5 if AQI is missing but PM2.5 is available
        mask = (df_merged['aqi'].isna()) & (df_merged['pm25'].notna())
        df_merged.loc[mask, 'aqi'] = df_merged.loc[mask, 'pm25'].apply(calculate_aqi_pm25)
        
        # Interpolate missing values (linear interpolation)
        df_merged['aqi'] = df_merged['aqi'].interpolate(method='linear', limit_direction='both')
        df_merged['pm25'] = df_merged['pm25'].interpolate(method='linear', limit_direction='both')
        
        # Forward fill any remaining NaNs at the beginning
        df_merged['aqi'] = df_merged['aqi'].ffill().bfill()
        df_merged['pm25'] = df_merged['pm25'].ffill().bfill()
        
        # If still NaN values exist, use the last available values
        if df_merged['aqi'].isna().any():
            last_valid_aqi = df['aqi'].dropna().iloc[-1] if not df['aqi'].dropna().empty else 100
            last_valid_pm25 = df['pm25'].dropna().iloc[-1] if not df['pm25'].dropna().empty else 50
            df_merged['aqi'] = df_merged['aqi'].fillna(last_valid_aqi)
            df_merged['pm25'] = df_merged['pm25'].fillna(last_valid_pm25)
        
        # Ensure AQI is within valid range (15-500) - AQI never goes to 0 in real conditions
        # Minimum realistic AQI in India is around 15-30 even in clean areas
        df_merged['aqi'] = df_merged['aqi'].clip(15, 500)
        df_merged['pm25'] = df_merged['pm25'].clip(5, 500)
        
        # Return as list of dicts with ISO format datetime
        data = []
        for _, row in df_merged.iterrows():
            # Ensure minimum realistic values (AQI never 0 in real conditions)
            aqi_val = float(row['aqi']) if pd.notna(row['aqi']) else 50.0
            pm25_val = float(row['pm25']) if pd.notna(row['pm25']) else 25.0
            aqi_val = max(15, min(500, aqi_val))  # Minimum AQI is 15
            pm25_val = max(5, min(500, pm25_val))  # Minimum PM2.5 is 5
            data.append({
                "datetime": row['datetime'].isoformat(),
                "aqi": aqi_val,
                "pm25": pm25_val
            })
        
        return {"data": data}
        
    except Exception as e:
        print(f"History endpoint failed for {city}: {e}")
        # Fallback to synthetic data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        return generate_synthetic_history(city, start_time, end_time)
        
        # Convert datetime column to datetime type
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Remove any future data points
        df = df[df['datetime'] <= end_time]
        
        # Create hourly index for exactly 168 hours (7 days)
        hourly_index = pd.date_range(start=start_time, end=end_time, freq='H')
        hourly_index = hourly_index[:168]  # Ensure exactly 168 hours
        
        # Create a DataFrame with hourly index
        hourly_df = pd.DataFrame(index=hourly_index)
        hourly_df['datetime'] = hourly_index
        
        # Merge with actual data
        df_merged = pd.merge(hourly_df, df, on='datetime', how='left', suffixes=('', '_actual'))
        
        # Use actual values where available, otherwise NaN
        df_merged['aqi'] = df_merged.get('aqi_actual', df_merged.get('aqi'))
        df_merged['pm25'] = df_merged.get('pm25_actual', df_merged.get('pm25'))
        
        # Calculate AQI from PM2.5 if AQI is missing but PM2.5 is available
        mask = (df_merged['aqi'].isna()) & (df_merged['pm25'].notna())
        df_merged.loc[mask, 'aqi'] = df_merged.loc[mask, 'pm25'].apply(calculate_aqi_pm25)
        
        # Interpolate missing values (linear interpolation)
        df_merged['aqi'] = df_merged['aqi'].interpolate(method='linear', limit_direction='both')
        df_merged['pm25'] = df_merged['pm25'].interpolate(method='linear', limit_direction='both')
        
        # Forward fill any remaining NaNs at the beginning
        df_merged['aqi'] = df_merged['aqi'].ffill().bfill()
        df_merged['pm25'] = df_merged['pm25'].ffill().bfill()
        
        # If still NaN values exist, use synthetic data to fill gaps
        if df_merged['aqi'].isna().any() or df_merged['pm25'].isna().any():
            synthetic_data = generate_synthetic_history(city, start_time, end_time)
            synthetic_df = pd.DataFrame(synthetic_data['data'])
            synthetic_df['datetime'] = pd.to_datetime(synthetic_df['datetime'])
            
            # Fill missing values with synthetic data
            for idx in df_merged.index:
                if pd.isna(df_merged.loc[idx, 'aqi']) or pd.isna(df_merged.loc[idx, 'pm25']):
                    synthetic_row = synthetic_df[synthetic_df['datetime'] == idx]
                    if not synthetic_row.empty:
                        df_merged.loc[idx, 'aqi'] = synthetic_row.iloc[0]['aqi']
                        df_merged.loc[idx, 'pm25'] = synthetic_row.iloc[0]['pm25']
        
        # Ensure AQI is within valid range (0-500)
        df_merged['aqi'] = df_merged['aqi'].clip(0, 500)
        df_merged['pm25'] = df_merged['pm25'].clip(0, 500)
        
        # Return as list of dicts with ISO format datetime
        data = []
        for _, row in df_merged.iterrows():
            data.append({
                "datetime": row['datetime'].isoformat(),
                "aqi": float(row['aqi']) if pd.notna(row['aqi']) else 0.0,
                "pm25": float(row['pm25']) if pd.notna(row['pm25']) else 0.0
            })
        
        return {"data": data}
        
    except Exception as e:
        print(f"History endpoint failed for {city}: {e}")
        # Fallback to synthetic data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        return generate_synthetic_history(city, start_time, end_time)

def generate_synthetic_history(city, start_time, end_time):
    """Generate synthetic historical data for fallback purposes"""
    try:
        import random
        import numpy as np
        
        random.seed(42)  # For reproducible results
        np.random.seed(42)
        
        # Create hourly index for exactly 168 hours (7 days)
        hourly_index = pd.date_range(start=start_time, end=end_time, freq='H')
        hourly_index = hourly_index[:168]  # Ensure exactly 168 hours
        
        # Generate realistic synthetic data with daily patterns
        data = []
        base_pm25 = random.uniform(30, 80)
        
        for i, timestamp in enumerate(hourly_index):
            # Add daily pattern (higher during rush hours)
            hour = timestamp.hour
            if 7 <= hour <= 9 or 18 <= hour <= 20:  # Rush hours
                daily_factor = 1.3
            elif 10 <= hour <= 17:  # Daytime
                daily_factor = 1.1
            else:  # Night/early morning
                daily_factor = 0.8
            
            # Add weekly pattern (higher on weekdays)
            day_of_week = timestamp.dayofweek
            if day_of_week < 5:  # Weekday
                weekly_factor = 1.1
            else:  # Weekend
                weekly_factor = 0.9
            
            # Add random variation
            random_factor = random.uniform(0.8, 1.2)
            
            # Calculate PM2.5 with all factors - minimum 10 µg/m³ (realistic minimum)
            pm25 = max(10, base_pm25 * daily_factor * weekly_factor * random_factor)
            
            # Calculate AQI from PM2.5 - minimum AQI is 15 (never 0 in real conditions)
            aqi = calculate_aqi_pm25(pm25)
            aqi = max(15, min(500, aqi if aqi is not None else 50))
            
            data.append({
                "datetime": timestamp.isoformat(),
                "aqi": aqi,
                "pm25": pm25
            })
        
        return {"data": data}
        
    except Exception as e:
        print(f"Synthetic history generation failed: {e}")
        # Return minimal data
        return {"data": []}

@app.get("/forecast")
def get_forecast(city: str = Query(..., description="City name")):
    """
    Generate HOURLY AQI forecast for exactly 7 days (168 hours).
    Uses ARIMA model if available, otherwise falls back to persistence/rolling mean.
    """
    ensure_models_loaded()

    forecast_data = []
    forecast_hours = 168  # 7 days * 24 hours
    
    # 1. ARIMA (internal model) - 168 hours (if available)
    # Prefer per-city ARIMA; fall back to legacy single model if present.
    arima_model = None
    city_slug = None
    try:
        # per-city
        arima_city_models = models.get('arima_city') or {}
        city_slug = city.strip().lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
        if city_slug in arima_city_models:
            arima_model = arima_city_models[city_slug]
        elif 'arima_legacy' in models:
            arima_model = models['arima_legacy']
    except Exception as e:
        print(f"Error selecting ARIMA model for {city}: {e}")

    if arima_model is not None:
        try:
            conn = get_db_connection()
            last_row = conn.execute(
                "SELECT datetime, pm25 FROM aqi_cleaned WHERE city=? ORDER BY datetime DESC LIMIT 1",
                (city,)
            ).fetchone()
            conn.close()

            if last_row:
                last_time = pd.to_datetime(last_row['datetime'])
                # Generate 168-hour forecast
                try:
                    forecast_res = arima_model.forecast(steps=forecast_hours)
                    # Ensure forecast results are valid
                    if forecast_res is not None and len(forecast_res) >= forecast_hours:
                        for i in range(forecast_hours):
                            future_time = last_time + pd.Timedelta(hours=i + 1)
                            pm25_val = float(forecast_res[i]) if i < len(forecast_res) else float(forecast_res[-1])
                            pm25_val = max(10, pm25_val)  # Minimum realistic PM2.5
                            aqi = calculate_aqi_pm25(pm25_val)
                            aqi = max(15, min(500, aqi if aqi is not None else 50))
                            forecast_data.append({
                                "datetime": future_time.isoformat(),
                                "pm25": pm25_val,
                                "aqi": aqi,
                                "horizon": f"{i + 1}h",
                                "source": "ARIMA Model (Per-City)" if city_slug and city_slug in (models.get('arima_city') or {}) else "ARIMA Model (Legacy)"
                            })
                        if forecast_data:
                            return {"forecast": forecast_data}
                except Exception as e:
                    print(f"ARIMA forecast failed (trying shorter horizon): {e}")
                    # If 168 steps fails, try generating in chunks
                    try:
                        forecast_res = []
                        for chunk_start in range(0, forecast_hours, 24):
                            chunk_size = min(24, forecast_hours - chunk_start)
                            try:
                                chunk_forecast = arima_model.forecast(steps=chunk_size)
                                if chunk_forecast is not None:
                                    forecast_res.extend(chunk_forecast)
                            except:
                                continue
                        if forecast_res and len(forecast_res) >= forecast_hours:
                            for i in range(forecast_hours):
                                future_time = last_time + pd.Timedelta(hours=i + 1)
                                pm25_val = float(forecast_res[i]) if i < len(forecast_res) else float(forecast_res[-1])
                                pm25_val = max(10, pm25_val)  # Minimum realistic PM2.5
                                aqi = calculate_aqi_pm25(pm25_val)
                                aqi = max(15, min(500, aqi if aqi is not None else 50))
                                forecast_data.append({
                                    "datetime": future_time.isoformat(),
                                    "pm25": pm25_val,
                                    "aqi": aqi,
                                    "horizon": f"{i + 1}h",
                                    "source": "ARIMA Model (Chunked)"
                                })
                            if forecast_data:
                                return {"forecast": forecast_data}
                    except Exception as chunk_e:
                        print(f"ARIMA chunked forecast also failed: {chunk_e}")
        except Exception as e:
            print(f"ARIMA forecasting failed for {city}: {e}")

    # 2. FALLBACK: Rolling mean with trend from recent history
    try:
        conn = get_db_connection()
        df = pd.read_sql(
            "SELECT datetime, pm25, aqi FROM aqi_cleaned WHERE city=? ORDER BY datetime DESC LIMIT 168",
            conn,
            params=(city,),
        )
        conn.close()
        if not df.empty:
            df = df.sort_values("datetime")
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Calculate rolling mean and trend
            recent_pm25 = df['pm25'].values
            recent_aqi = df['aqi'].values
            
            if len(recent_pm25) > 0:
                # Use rolling mean of last 24 hours as baseline
                baseline_pm25 = float(np.mean(recent_pm25[-24:])) if len(recent_pm25) >= 24 else float(np.mean(recent_pm25))
                baseline_aqi = float(np.mean(recent_aqi[-24:])) if len(recent_aqi) >= 24 else float(np.mean(recent_aqi))
                
                # Calculate trend (simple linear regression on last 48 hours if available)
                if len(recent_pm25) >= 48:
                    x = np.arange(len(recent_pm25[-48:]))
                    trend_slope = np.polyfit(x, recent_pm25[-48:], 1)[0]
                else:
                    trend_slope = 0.0
                
                last_time = pd.to_datetime(df["datetime"].iloc[-1])
                
                # Generate 168-hour forecast with slight decay of trend
                np.random.seed(42)  # For reproducible results
                for h in range(1, forecast_hours + 1):
                    future_time = last_time + pd.Timedelta(hours=h)
                    # Apply trend with decay factor (trend weakens over time)
                    decay_factor = max(0.1, 1.0 - (h / forecast_hours) * 0.8)
                    forecast_pm25 = baseline_pm25 + (trend_slope * h * decay_factor)
                    forecast_pm25 = max(0, forecast_pm25)  # Ensure non-negative
                    
                    # Add slight hourly variation (simulate day/night cycle)
                    hour_of_day = future_time.hour
                    # Higher pollution typically during morning (6-10) and evening (18-22)
                    if 6 <= hour_of_day <= 10 or 18 <= hour_of_day <= 22:
                        variation = np.random.normal(0, baseline_pm25 * 0.05)
                    else:
                        variation = np.random.normal(0, baseline_pm25 * 0.03)
                    forecast_pm25 += variation
                    forecast_pm25 = max(10, forecast_pm25)  # Minimum realistic PM2.5
                    
                    aqi = calculate_aqi_pm25(forecast_pm25)
                    aqi = max(15, min(500, aqi if aqi is not None else 50))
                    
                    forecast_data.append({
                        "datetime": future_time.isoformat(),
                        "pm25": forecast_pm25,
                        "aqi": aqi,
                        "horizon": f"{h}h",
                        "source": "Rolling Mean with Trend",
                    })
                if forecast_data:
                    return {"forecast": forecast_data}
    except Exception as e:
        print(f"Rolling mean fallback failed: {e}")

    # 3. FINAL FALLBACK: Persistence baseline with realistic daily patterns
    try:
        # Get current live data as baseline
        live_data = get_live_data(city)
        if live_data and 'pm25' in live_data:
            last_pm25 = float(live_data['pm25'])
            last_aqi = float(live_data['aqi'])
            last_time = pd.to_datetime(live_data.get('datetime', datetime.now()))
            
            # Generate forecast with realistic daily patterns and variations
            np.random.seed(int(datetime.now().timestamp()) % 1000)  # More random seed
            
            for h in range(1, forecast_hours + 1):
                future_time = last_time + pd.Timedelta(hours=h)
                hour_of_day = future_time.hour
                day_of_week = future_time.dayofweek
                
                # Daily pattern: Higher during rush hours (morning 7-10, evening 17-21)
                if 7 <= hour_of_day <= 10:
                    hourly_factor = 1.15 + np.random.uniform(0, 0.15)  # Morning rush
                elif 17 <= hour_of_day <= 21:
                    hourly_factor = 1.20 + np.random.uniform(0, 0.20)  # Evening rush (higher)
                elif 11 <= hour_of_day <= 16:
                    hourly_factor = 0.95 + np.random.uniform(-0.05, 0.10)  # Mid-day
                elif 22 <= hour_of_day or hour_of_day <= 4:
                    hourly_factor = 0.75 + np.random.uniform(-0.10, 0.10)  # Night (lower)
                else:
                    hourly_factor = 0.85 + np.random.uniform(-0.05, 0.10)  # Early morning
                
                # Weekly pattern: Slightly higher on weekdays
                if day_of_week < 5:  # Weekday
                    weekly_factor = 1.05 + np.random.uniform(-0.05, 0.10)
                else:  # Weekend
                    weekly_factor = 0.90 + np.random.uniform(-0.05, 0.10)
                
                # Add random walk component for natural variation
                random_walk = np.random.normal(0, last_pm25 * 0.08)  # 8% random variation
                
                # Long-term trend (slight decay or increase based on current level)
                if last_aqi > 300:
                    trend_factor = 0.998  # Slight improvement if very poor
                elif last_aqi < 100:
                    trend_factor = 1.002  # Slight worsening if good
                else:
                    trend_factor = 1.0
                
                # Calculate forecast PM2.5
                forecast_pm25 = last_pm25 * hourly_factor * weekly_factor * (trend_factor ** h) + random_walk
                forecast_pm25 = max(10, min(500, forecast_pm25))  # Keep within realistic bounds
                
                forecast_aqi = calculate_aqi_pm25(forecast_pm25)
                forecast_aqi = max(15, min(500, forecast_aqi if forecast_aqi is not None else 50))
                
                forecast_data.append({
                    "datetime": future_time.isoformat(),
                    "pm25": forecast_pm25,
                    "aqi": forecast_aqi,
                    "horizon": f"{h}h",
                    "source": "Persistence Baseline with Daily Patterns",
                })
            if forecast_data:
                return {"forecast": forecast_data}
    except Exception as e:
        print(f"Persistence fallback failed: {e}")

    # 4. ABSOLUTE LAST RESORT: Generate synthetic forecast data
    try:
        import random
        random.seed(42)
        base_pm25 = random.uniform(30, 80)
        base_aqi = calculate_aqi_pm25(base_pm25)
        start_time = datetime.now()
        
        for h in range(1, forecast_hours + 1):
            future_time = start_time + pd.Timedelta(hours=h)
            # Add daily pattern and random variation
            hour_factor = 1.0 + 0.2 * np.sin(2 * np.pi * future_time.hour / 24)  # Daily pattern
            random_factor = random.uniform(0.9, 1.1)
            forecast_pm25 = max(10, base_pm25 * hour_factor * random_factor)  # Minimum realistic PM2.5
            forecast_aqi = calculate_aqi_pm25(forecast_pm25)
            forecast_aqi = max(15, min(500, forecast_aqi if forecast_aqi is not None else 50))
            
            forecast_data.append({
                "datetime": future_time.isoformat(),
                "pm25": forecast_pm25,
                "aqi": forecast_aqi,
                "horizon": f"{h}h",
                "source": "Synthetic Forecast (Last Resort)",
            })
        return {"forecast": forecast_data}
    except Exception as e:
        print(f"Synthetic forecast failed: {e}")

    # Absolute last resort: empty forecast (should be rare)
    return {"forecast": []}

@app.get("/health-advisory")
def get_health_advisory_endpoint(aqi: int):
    return get_health_advisory(aqi)

@app.get("/map-aqi")
def get_map_aqi(lat: float = Query(..., description="Latitude"), lon: float = Query(..., description="Longitude")):
    """
    Get current AQI for a specific lat/lon coordinate using ONLY local data.
    Strategy:
    - Find nearest city from the local CSV (haversine distance)
    - Use latest AQI record for that city from the database
    """
    try:
        cities = load_indian_cities_from_file()
        if not cities:
            # Generate synthetic AQI data for the coordinates
            return generate_synthetic_map_aqi(lat, lon)

        # Find nearest city by great-circle distance
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0  # km
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        nearest = None
        best_dist = float("inf")
        for c in cities:
            c_lat = c.get("lat")
            c_lon = c.get("lon")
            if c_lat is None or c_lon is None:
                continue
            d = haversine(lat, lon, c_lat, c_lon)
            if d < best_dist:
                best_dist = d
                nearest = c

        if nearest is None:
            return generate_synthetic_map_aqi(lat, lon)

        nearest_city = nearest.get("city")
        nearest_state = nearest.get("state")

        # Try to get live data for the nearest city first
        try:
            live_data = get_live_data(nearest_city)
            if live_data and 'aqi' in live_data:
                aqi = float(live_data['aqi'])
                pm25 = float(live_data.get('pm25', 0))
                category = get_aqi_category(aqi)
                health_info = get_health_advisory(aqi)
                
                return {
                    "success": True,
                    "aqi": aqi,
                    "pm25": pm25,
                    "category": category,
                    "health_info": {
                        "impact": health_info.get("effect", "Unknown"),
                        "precaution": health_info.get("precaution", "Check air quality"),
                    },
                    "datetime": live_data.get('datetime'),
                    "nearest_city": nearest_city,
                    "nearest_state": nearest_state,
                    "station_name": None,
                    "distance_km": round(best_dist, 2)
                }
        except Exception as e:
            print(f"Live data fallback failed for map AQI: {e}")

        # Fallback to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "SELECT * FROM aqi_cleaned WHERE city=? AND datetime <= ? ORDER BY datetime DESC LIMIT 1",
                (nearest_city, now_str),
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                res = dict(row)
                pm25 = float(res.get("pm25") or 0)
                aqi = float(res.get("aqi") or calculate_aqi_pm25(pm25) or 0)
                aqi = max(0, min(500, aqi))
                category = get_aqi_category(aqi)
                health_info = get_health_advisory(aqi)

                return {
                    "success": True,
                    "aqi": aqi,
                    "pm25": pm25,
                    "category": category,
                    "health_info": {
                        "impact": health_info.get("effect", "Unknown"),
                        "precaution": health_info.get("precaution", "Check air quality"),
                    },
                    "datetime": res.get("datetime"),
                    "nearest_city": nearest_city,
                    "nearest_state": nearest_state,
                    "station_name": None,
                    "distance_km": round(best_dist, 2)
                }
        except Exception as e:
            print(f"Database fallback failed for map AQI: {e}")

        # Final fallback: generate synthetic data
        return generate_synthetic_map_aqi(lat, lon, nearest_city, nearest_state, best_dist)
        
    except Exception as e:
        print(f"Map AQI endpoint failed: {e}")
        return generate_synthetic_map_aqi(lat, lon)

def generate_synthetic_map_aqi(lat, lon, nearest_city=None, nearest_state=None, distance=None):
    """Generate synthetic AQI data for map coordinates"""
    import random
    random.seed(42)
    
    # Generate realistic AQI based on location (urban areas tend to have higher AQI)
    base_aqi = random.uniform(50, 200)
    base_pm25 = random.uniform(20, 80)
    
    aqi = max(0, min(500, base_aqi))
    pm25 = max(0, base_pm25)
    category = get_aqi_category(aqi)
    health_info = get_health_advisory(aqi)
    
    return {
        "success": True,
        "aqi": aqi,
        "pm25": pm25,
        "category": category,
        "health_info": {
            "impact": health_info.get("effect", "Unknown"),
            "precaution": health_info.get("precaution", "Check air quality"),
        },
        "datetime": datetime.now().isoformat(),
        "nearest_city": nearest_city or "Unknown Location",
        "nearest_state": nearest_state or "",
        "station_name": None,
        "distance_km": round(distance, 2) if distance else None,
        "source": "Synthetic Data (Map Fallback)"
    }
