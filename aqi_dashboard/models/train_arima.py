
import os
import pickle
import sqlite3

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.arima.model import ARIMA

DB_PATH = os.path.join(os.path.dirname(__file__), "../database/aqi.db")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved")


def slugify_city(name: str) -> str:
    """Create a filesystem-safe slug for a city name."""
    return (
        name.strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def train_arima_for_all_cities(min_points: int = 200):
    """
    Train a separate ARIMA model for each city present in aqi_cleaned.

    - Uses hourly PM2.5 time series per city.
    - Skips cities with very little data (min_points).
    - Saves models as saved/arima_<city_slug>.pkl
    """
    print("Starting ARIMA training for all cities...")
    if not os.path.exists(DB_PATH):
        print("Database not found. Run ingestion first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cities_df = pd.read_sql("SELECT DISTINCT city FROM aqi_cleaned ORDER BY city", conn)
    cities = [c for c in cities_df["city"].dropna().unique()]

    if not cities:
        print("No cities found in aqi_cleaned.")
        conn.close()
        return

    os.makedirs(MODELS_DIR, exist_ok=True)

    for city in cities:
        print(f"\n=== Training ARIMA for city: {city} ===")
        df = pd.read_sql(
            "SELECT datetime, pm25 FROM aqi_cleaned WHERE city=? ORDER BY datetime",
            conn,
            params=(city,),
        )
        if df.empty:
            print(f"  Skipping {city}: no data.")
            continue

        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").asfreq("H")
        df["pm25"] = df["pm25"].ffill()

        if len(df) < min_points:
            print(f"  Skipping {city}: only {len(df)} points (<{min_points}).")
            continue

        # Train/test split
        train_size = int(len(df) * 0.8)
        train, test = df.iloc[:train_size], df.iloc[train_size:]

        print(f"  Training ARIMA(5,1,0) on {len(train)} points...")
        try:
            model = ARIMA(train["pm25"], order=(5, 1, 0))
            model_fit = model.fit()
        except Exception as e:
            print(f"  Failed to fit ARIMA for {city}: {e}")
            continue

        # Evaluate
        if not test.empty:
            forecast = model_fit.forecast(steps=len(test))
            rmse = np.sqrt(mean_squared_error(test["pm25"], forecast))
            print(f"  ARIMA RMSE for {city}: {rmse:.3f}")
        else:
            print(f"  Not enough test data to compute RMSE for {city}.")

        # Save model per city
        city_slug = slugify_city(city)
        model_path = os.path.join(MODELS_DIR, f"arima_{city_slug}.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model_fit, f)
        print(f"  Saved model to {model_path}")

    conn.close()
    print("\nARIMA training for all cities complete.")


if __name__ == "__main__":
    train_arima_for_all_cities()
