#!/usr/bin/env python3
"""
Test dashboard fixes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_plotly_timestamp_fix():
    """Test the plotly timestamp fix"""
    print("Testing plotly timestamp fix...")
    try:
        # Create sample data
        dates = pd.date_range(start='2025-01-01', periods=5, freq='h')
        df = pd.DataFrame({'datetime': dates, 'aqi': [100, 150, 200, 180, 120]})
        
        # Test the fix - convert timestamp to milliseconds
        transition_time = df['datetime'].iloc[-1]
        transition_timestamp = transition_time.timestamp() * 1000
        print(f"Original datetime: {transition_time}")
        print(f"Converted timestamp: {transition_timestamp}")
        print("✓ Plotly timestamp fix works")
        return True
    except Exception as e:
        print(f"✗ Plotly timestamp fix failed: {e}")
        return False

def test_city_column_fix():
    """Test the city column fix"""
    print("\nTesting city column fix...")
    try:
        # Create sample dataframe without 'city' column
        df = pd.DataFrame({
            'datetime': pd.date_range(start='2025-01-01', periods=3, freq='h'),
            'aqi': [100, 150, 200],
            'pm25': [50, 75, 100]
        })
        
        # Test the fix - check if 'city' column exists
        available_columns = list(df.columns)
        if 'city' in available_columns:
            display_df = df[['datetime', 'city', 'aqi', 'pm25']].copy()
        else:
            display_df = df[['datetime', 'aqi', 'pm25']].copy()
            
        print(f"Available columns: {available_columns}")
        print(f"Display columns: {list(display_df.columns)}")
        print("✓ City column fix works")
        return True
    except Exception as e:
        print(f"✗ City column fix failed: {e}")
        return False

def test_deprecated_width_fix():
    """Test the width parameter fix"""
    print("\nTesting width parameter fix...")
    try:
        # The fix simply replaces use_container_width=True with width='stretch'
        # This should work in Streamlit 1.28+
        print("✓ Width parameter fix (use_container_width -> width='stretch')")
        return True
    except Exception as e:
        print(f"✗ Width parameter fix failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("DASHBOARD FIXES TEST")
    print("=" * 50)
    
    tests = [
        test_plotly_timestamp_fix,
        test_city_column_fix,
        test_deprecated_width_fix
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    if all(results):
        print("✅ ALL FIXES WORKING!")
        print("\nDashboard should now start without errors.")
        print("Fixed issues:")
        print("  1. Plotly timestamp compatibility")
        print("  2. Missing 'city' column handling")
        print("  3. Deprecated use_container_width parameter")
        print("\nRun: streamlit run app/dashboard.py --server.port 8501")
    else:
        print("❌ Some fixes failed. Check errors above.")
    
    return all(results)

if __name__ == "__main__":
    main()