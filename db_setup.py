import sqlite3
import os
from config import DB_PATH

def setup_database():
    print(f"Setting up database at: {DB_PATH}")
    
    # Ensure any existing DB is replaced or we just create if not exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create stock_prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)
    
    # Realistic stock data for AAPL, MSFT, GOOGL
    data = [
        # AAPL
        ('AAPL', '2026-07-01', 180.50, 182.00, 179.80, 181.20, 52000000),
        ('AAPL', '2026-07-02', 181.30, 183.50, 180.90, 183.10, 48000000),
        ('AAPL', '2026-07-03', 182.90, 184.20, 182.10, 183.90, 45000000),
        ('AAPL', '2026-07-06', 184.00, 185.80, 183.50, 185.20, 50000000),
        ('AAPL', '2026-07-07', 185.10, 186.50, 184.30, 186.00, 47000000),
        ('AAPL', '2026-07-08', 185.90, 187.20, 185.00, 186.80, 49000000),
        ('AAPL', '2026-07-09', 187.00, 188.50, 186.20, 188.10, 55000000),
        ('AAPL', '2026-07-10', 188.00, 189.90, 187.50, 189.50, 60000000),
        # MSFT
        ('MSFT', '2026-07-01', 340.20, 342.50, 339.10, 341.80, 22000000),
        ('MSFT', '2026-07-02', 342.00, 344.00, 341.20, 343.50, 20000000),
        ('MSFT', '2026-07-03', 343.80, 345.20, 343.00, 344.90, 18000000),
        ('MSFT', '2026-07-06', 345.00, 347.10, 344.50, 346.80, 21000000),
        ('MSFT', '2026-07-07', 347.00, 348.50, 346.10, 348.00, 19000000),
        ('MSFT', '2026-07-08', 348.20, 349.90, 347.50, 349.50, 23000000),
        ('MSFT', '2026-07-09', 349.80, 352.00, 349.00, 351.40, 25000000),
        ('MSFT', '2026-07-10', 351.50, 353.80, 350.90, 353.20, 24000000),
        # GOOGL
        ('GOOGL', '2026-07-01', 120.10, 121.50, 119.80, 120.90, 28000000),
        ('GOOGL', '2026-07-02', 121.00, 122.80, 120.70, 122.50, 25000000),
        ('GOOGL', '2026-07-03', 122.60, 123.50, 122.10, 123.20, 22000000),
        ('GOOGL', '2026-07-06', 123.40, 124.80, 123.00, 124.50, 26000000),
        ('GOOGL', '2026-07-07', 124.60, 125.50, 124.10, 125.20, 24000000),
        ('GOOGL', '2026-07-08', 125.30, 126.20, 124.90, 125.80, 27000000),
        ('GOOGL', '2026-07-09', 126.00, 127.50, 125.80, 127.10, 30000000),
        ('GOOGL', '2026-07-10', 127.20, 128.90, 126.90, 128.50, 32000000),
    ]
    
    cursor.executemany("""
        INSERT OR REPLACE INTO stock_prices (ticker, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, data)
    
    conn.commit()
    conn.close()
    print("Database populate complete.")

if __name__ == "__main__":
    setup_database()
