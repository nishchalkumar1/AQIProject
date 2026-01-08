
import pandas as pd
import numpy as np
import sqlite3
import pickle
import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error

DB_PATH = os.path.join(os.path.dirname(__file__), '../database/aqi.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'saved/lstm_model.h5')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'saved/scaler.pkl')

def create_dataset(dataset, look_back=24, forecast_horizon=24):
    X, Y = [], []
    for i in range(len(dataset) - look_back - forecast_horizon + 1):
        a = dataset[i:(i + look_back), 0]
        X.append(a)
        Y.append(dataset[(i + look_back):(i + look_back + forecast_horizon), 0])
    return np.array(X), np.array(Y)

def train_lstm():
    print("Loading data for LSTM training...")
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT datetime, pm25 FROM aqi_cleaned WHERE city='Delhi' ORDER BY datetime", conn)
    conn.close()
    
    if df.empty:
        print("No data found.")
        return
        
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')
    data = df['pm25'].values.astype('float32')
    data = data.reshape(-1, 1)
    
    # Normalize
    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(data)
    
    # Save scaler
    os.makedirs(os.path.dirname(SCALER_PATH), exist_ok=True)
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
        
    # Split
    train_size = int(len(dataset) * 0.8)
    train, test = dataset[:train_size], dataset[train_size:]
    
    look_back = 24
    forecast_horizon = 24 # predicting next 24 hours
    
    X_train, Y_train = create_dataset(train, look_back, forecast_horizon)
    X_test, Y_test = create_dataset(test, look_back, forecast_horizon)
    
    # Reshape input to be [samples, time steps, features]
    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
    
    print(f"Training LSTM model... Input shape: {X_train.shape}")
    
    model = Sequential()
    model.add(LSTM(50, input_shape=(look_back, 1)))
    model.add(Dense(forecast_horizon))
    model.compile(loss='mean_squared_error', optimizer='adam')
    
    model.fit(X_train, Y_train, epochs=20, batch_size=32, verbose=1, validation_data=(X_test, Y_test))
    
    # Evaluate
    train_predict = model.predict(X_train)
    test_predict = model.predict(X_test)
    
    # Inverse transform
    # Need to reshape for inverse transform
    # Predict shape is (N, 24). Scaler expects (N, 1). 
    # We invert one step at a time or reshape. 
    # Actually simpler: standard scaler inversion on flattened array or just keep as is for metric calc if scaled.
    # Proper way:
    # rmse = np.sqrt(mean_squared_error(Y_test, test_predict))
    # print(f"LSTM Scaled RMSE: {rmse}")
    
    print(f"Saving model to {MODEL_PATH}")
    model.save(MODEL_PATH)
    print("LSTM training complete.")

if __name__ == "__main__":
    train_lstm()
