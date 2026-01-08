import pandas as pd
import sqlite3
import requests
import os
import sys
from datetime import datetime, timedelta

# Append app to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.utils import calculate_aqi_pm25

DB_PATH = os.path.join(os.path.dirname(__file__), '../database/aqi.db')

def ingest_data():
    # City Coordinates
    CITY_COORDS = {
        "Delhi": (28.61, 77.20),
        "Mumbai": (19.07, 72.87),
        "Bengaluru": (12.97, 77.59),
        "Chennai": (13.08, 80.27),
        "Kolkata": (22.57, 88.36),
        "Hyderabad": (17.38, 78.48),
        "Pune": (18.52, 73.85),
        "Ahmedabad": (23.02, 72.57),
        "Jaipur": (26.91, 75.78),
        "Lucknow": (26.84, 80.94)
    }

    print("Connecting to database...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Test database connection first
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Quick integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] != 'ok':
            raise sqlite3.DatabaseError(f"Database integrity check failed: {result[0]}")
    except sqlite3.DatabaseError as e:
        print(f"ERROR: Database is corrupted: {e}")
        print("Please run: python scripts/fix_database.py")
        raise
    
    # Create Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aqi_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT,
        datetime TIMESTAMP,
        pm25 REAL,
        temp REAL,
        humidity REAL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aqi_cleaned (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT,
        datetime TIMESTAMP,
        pm25 REAL,
        aqi REAL,
        hour INTEGER,
        day_of_week TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aqi_forecast (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT,
        datetime TIMESTAMP,
        horizon TEXT,
        predicted_aqi REAL,
        model_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Clear existing data
    print("Clearing old data...")
    cursor.execute("DELETE FROM aqi_raw")
    cursor.execute("DELETE FROM aqi_cleaned")
    cursor.execute("DELETE FROM aqi_forecast")
    conn.commit()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    for city_name, (lat, lon) in CITY_COORDS.items():
        print(f"Fetching data for {city_name}...")
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly=pm2_5&timezone=Asia%2FKolkata"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch for {city_name}: {response.status_code}")
                continue
                
            data = response.json()
            hourly = data.get('hourly', {})
            times = hourly.get('time', [])
            pm25_values = hourly.get('pm2_5', [])
            
            if not times:
                print(f"No data for {city_name}")
                continue
                
            df = pd.DataFrame({
                'datetime': times,
                'pm25': pm25_values
            })
            
            # Process
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime')
            df['city'] = city_name
            
            # Handle missing
            df['pm25'] = df['pm25'].ffill().bfill()
            df['temp'] = None
            df['humidity'] = None
            
            # Calculate AQI
            df['aqi'] = df['pm25'].apply(calculate_aqi_pm25)
            
            # Time features
            df['hour'] = df['datetime'].dt.hour
            df['day_of_week'] = df['datetime'].dt.day_name()
            
            # Insert
            raw_cols = ['city', 'datetime', 'pm25', 'temp', 'humidity']
            df[raw_cols].to_sql('aqi_raw', conn, if_exists='append', index=False)
            
            cleaned_cols = ['city', 'datetime', 'pm25', 'aqi', 'hour', 'day_of_week']
            df[cleaned_cols].to_sql('aqi_cleaned', conn, if_exists='append', index=False)
            
            print(f"Ingested {len(df)} records for {city_name}")
            
        except Exception as e:
            print(f"Error for {city_name}: {e}")
            
    conn.commit()
    conn.close()
    print("All cities ingestion complete.")

if __name__ == "__main__":
    ingest_data()
