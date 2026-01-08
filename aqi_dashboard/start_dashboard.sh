#!/bin/bash

echo "===================================="
echo "    VAYUTEL AQI DASHBOARD"
echo "===================================="
echo
echo "Starting AQI Backend Server..."
echo

# Start backend in background
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo
echo "Waiting for backend to start..."
sleep 5

echo
echo "Starting Streamlit Dashboard..."
echo
echo "Dashboard will open at: http://localhost:8501"
echo "API will be running at: http://localhost:8000"
echo
echo "Press Ctrl+C to stop the servers"
echo "===================================="

# Start dashboard
streamlit run app/dashboard.py --server.port 8501

# Clean up background process on exit
kill $BACKEND_PID 2>/dev/null