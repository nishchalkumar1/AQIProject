#!/usr/bin/env python3
"""
Test script for AQI API endpoints
"""

import requests
import json
from datetime import datetime

API_URL = "http://127.0.0.1:8000"

def test_endpoint(endpoint, params=None):
    """Test a single API endpoint"""
    try:
        url = f"{API_URL}{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        
        print(f"\n{'='*50}")
        print(f"Testing: {endpoint}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Validate response structure
            if endpoint == "/live-data":
                required_keys = ["aqi", "pm25", "city", "datetime", "source"]
                if all(key in data for key in required_keys):
                    print("✓ Live data structure valid")
                    print(f"  AQI: {data.get('aqi')}")
                    print(f"  PM2.5: {data.get('pm25')}")
                    print(f"  Source: {data.get('source')}")
                else:
                    print("✗ Live data structure invalid")
                    
            elif endpoint == "/forecast":
                if "forecast" in data and isinstance(data["forecast"], list):
                    print(f"✓ Forecast data valid ({len(data['forecast'])} points)")
                    if data["forecast"]:
                        first_point = data["forecast"][0]
                        print(f"  First forecast point: {first_point}")
                else:
                    print("✗ Forecast data structure invalid")
                    
            elif endpoint == "/history":
                if "data" in data and isinstance(data["data"], list):
                    print(f"✓ History data valid ({len(data['data'])} points)")
                    if data["data"]:
                        first_point = data["data"][0]
                        print(f"  First history point: {first_point}")
                else:
                    print("✗ History data structure invalid")
                    
            elif endpoint == "/weather":
                required_keys = ["temperature", "humidity", "weather_description", "source"]
                if all(key in data for key in required_keys):
                    print("✓ Weather data structure valid")
                    print(f"  Temperature: {data.get('temperature')}°C")
                    print(f"  Humidity: {data.get('humidity')}%")
                    print(f"  Weather: {data.get('weather_description')}")
                else:
                    print("✗ Weather data structure invalid")
                    
            elif endpoint == "/map-aqi":
                if "success" in data and data["success"]:
                    print("✓ Map AQI data valid")
                    print(f"  AQI: {data.get('aqi')}")
                    print(f"  Nearest city: {data.get('nearest_city')}")
                else:
                    print("✗ Map AQI data invalid")
                    
            elif endpoint == "/cities":
                if "cities" in data and isinstance(data["cities"], list):
                    print(f"✓ Cities data valid ({len(data['cities'])} cities)")
                    if data["cities"]:
                        print(f"  First city: {data['cities'][0]}")
                else:
                    print("✗ Cities data structure invalid")
                    
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to API at {API_URL}")
        print("Make sure the FastAPI server is running on port 8000")
    except Exception as e:
        print(f"✗ Test failed: {e}")

def main():
    """Run all API tests"""
    print("AQI API Endpoint Testing")
    print(f"Testing API at: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test endpoints
    test_endpoint("/")
    test_endpoint("/cities")
    test_endpoint("/live-data", {"city": "Delhi"})
    test_endpoint("/history", {"city": "Delhi", "period": "7d"})
    test_endpoint("/forecast", {"city": "Delhi"})
    test_endpoint("/weather", {"city": "Delhi"})
    test_endpoint("/map-aqi", {"lat": 28.61, "lon": 77.20})
    test_endpoint("/health-advisory", {"aqi": 150})
    
    print(f"\n{'='*50}")
    print("Testing complete!")
    print("\nTo start the API server, run:")
    print("cd aqi_dashboard")
    print("python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()