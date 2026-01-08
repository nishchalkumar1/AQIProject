# Interactive AQI Map - Setup & Usage Guide

## Overview
The Interactive Map feature allows users to click anywhere on a map and instantly view the current AQI for that exact location using real-time AQI data from Open-Meteo API.

## Features
- ✅ **Click anywhere on the map** to get AQI for that location
- ✅ **Real-time AQI data** from Open-Meteo Air Quality API
- ✅ **Indian AQI standards** (0-500 scale)
- ✅ **Color-coded markers** based on AQI severity
- ✅ **Health impact & precaution** information
- ✅ **Dark theme** compatible with VayuTel dashboard

## Installation

### Required Packages
```bash
pip install folium streamlit-folium
```

## How to Use

1. **Start the Backend API** (if not already running):
   ```bash
   cd aqi_dashboard
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start the Streamlit Dashboard**:
   ```bash
   streamlit run app/dashboard.py
   ```

3. **Navigate to Interactive Map**:
   - Click on "🗺️ Interactive Map" in the sidebar navigation

4. **Get AQI for a Location**:
   - **Method 1**: Click anywhere on the map
     - The coordinates will be captured automatically
     - AQI data will be fetched and displayed
     - A color-coded marker will appear on the map
   
   - **Method 2**: Enter coordinates manually
     - Enter latitude and longitude in the input fields
     - Click "🔍 Get AQI" button
     - Results will be displayed above the map

## AQI Color Coding

The map markers use Indian AQI color standards:
- 🟢 **Green** (0-50): Good
- 🔵 **Blue** (51-100): Satisfactory
- 🟠 **Orange** (101-200): Moderate
- 🔴 **Red** (201-300): Poor
- 🟥 **Dark Red** (301-400): Very Poor
- 🟤 **Maroon** (401-500): Severe

## API Endpoints

### Backend Endpoint
- **GET** `/map-aqi?lat={latitude}&lon={longitude}`
  - Returns current AQI, PM2.5, category, and health info for given coordinates

### External API Used
- **Open-Meteo Air Quality API**: `https://air-quality-api.open-meteo.com/v1/air-quality`
  - Provides real-time PM2.5 data for any lat/lon coordinate
  - Data is converted to Indian AQI using CPCB standards

## Technical Details

### Map Library
- **Folium**: Python library for interactive maps
- **Streamlit-Folium**: Streamlit component for displaying Folium maps
- Uses **CartoDB Dark Matter** tiles for dark theme compatibility

### AQI Calculation
- PM2.5 data from Open-Meteo is converted to Indian AQI using CPCB breakpoints
- Calculation function: `calculate_aqi_pm25()` in `app/utils.py`

### Error Handling
- If AQI data is unavailable, an error message is displayed
- Backend API errors are gracefully handled
- Network timeouts are handled with user-friendly messages

## Troubleshooting

### Map Not Displaying
- Ensure `folium` and `streamlit-folium` are installed
- Check that backend API is running on port 8000
- Refresh the Streamlit page

### AQI Data Not Available
- Check internet connection (Open-Meteo API requires internet)
- Verify backend API is running
- Try clicking a different location (some areas may not have data)

### Import Errors
- Run: `pip install folium streamlit-folium`
- Restart Streamlit after installation

## Notes
- The map uses OpenStreetMap/CartoDB tiles (no API key required)
- AQI data is fetched in real-time from Open-Meteo API
- Only one marker is displayed at a time (clicking replaces previous marker)
- Map is centered on India by default (coordinates: 20.5937°N, 78.9629°E)

