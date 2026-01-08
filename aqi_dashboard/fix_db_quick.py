"""
Quick Database Fix - Run this to fix corrupted database
"""
import os
import sqlite3
import shutil
from datetime import datetime

DB_PATH = os.path.join('database', 'aqi.db')
DB_DIR = os.path.dirname(DB_PATH)

print("=" * 60)
print("Quick Database Fix")
print("=" * 60)

# Backup and remove corrupted database
if os.path.exists(DB_PATH):
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n1. Backing up corrupted database...")
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"   ✓ Backup saved to: {backup_path}")
    except:
        print(f"   ⚠ Could not create backup")
    
    print(f"\n2. Removing corrupted database...")
    try:
        os.remove(DB_PATH)
        print(f"   ✓ Removed corrupted database")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("\nPlease manually delete the file and run this script again.")
        input("Press Enter to exit...")
        exit(1)

# Create new database
print(f"\n3. Creating new database...")
os.makedirs(DB_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

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

conn.commit()
conn.close()

print(f"   ✓ Database created successfully!")

print("\n" + "=" * 60)
print("Database fixed! Now run:")
print("  python scripts/ingest_data.py")
print("=" * 60)
input("\nPress Enter to exit...")

