"""
Database Repair Script
Fixes corrupted SQLite database by recreating it
"""
import os
import sqlite3
import shutil
from datetime import datetime

# Get database path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(SCRIPT_DIR, '../database')
DB_PATH = os.path.join(DB_DIR, 'aqi.db')
DB_BACKUP_PATH = os.path.join(DB_DIR, f'aqi_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')

def test_database(db_path):
    """Test if database is valid"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Try to query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        return True, tables
    except sqlite3.DatabaseError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def create_database(db_path):
    """Create a fresh database with all required tables"""
    print("Creating new database...")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_city_datetime ON aqi_cleaned(city, datetime)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON aqi_raw(city)')
    
    conn.commit()
    conn.close()
    print("Database created successfully!")

def fix_database():
    """Main function to fix corrupted database"""
    print("=" * 50)
    print("Database Repair Tool")
    print("=" * 50)
    print()
    
    # Check if database exists
    if os.path.exists(DB_PATH):
        print(f"Found database at: {DB_PATH}")
        
        # Test if database is valid
        is_valid, result = test_database(DB_PATH)
        
        if is_valid:
            print("✓ Database is valid!")
            print(f"  Found tables: {[t[0] for t in result]}")
            response = input("\nDatabase appears to be valid. Recreate anyway? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        else:
            print(f"✗ Database is corrupted: {result}")
            print("  Will recreate database...")
        
        # Backup corrupted database
        try:
            print(f"\nBacking up corrupted database to: {DB_BACKUP_PATH}")
            shutil.copy2(DB_PATH, DB_BACKUP_PATH)
            print("✓ Backup created")
        except Exception as e:
            print(f"⚠ Warning: Could not create backup: {e}")
        
        # Remove corrupted database
        try:
            print(f"\nRemoving corrupted database...")
            os.remove(DB_PATH)
            print("✓ Old database removed")
        except Exception as e:
            print(f"✗ Error removing database: {e}")
            print("  Please manually delete the file and try again.")
            return
    else:
        print(f"Database not found at: {DB_PATH}")
        print("Creating new database...")
    
    # Create new database
    create_database(DB_PATH)
    
    # Verify new database
    is_valid, result = test_database(DB_PATH)
    if is_valid:
        print("\n✓ New database created and verified!")
        print(f"  Tables: {[t[0] for t in result]}")
        print("\n" + "=" * 50)
        print("Next steps:")
        print("1. Run: python scripts/ingest_data.py")
        print("2. Run: python models/train_arima.py")
        print("3. Run: python models/train_lstm.py")
        print("=" * 50)
    else:
        print(f"\n✗ Error: New database is also invalid: {result}")
        print("  Please check file permissions and disk space.")

if __name__ == "__main__":
    try:
        fix_database()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

