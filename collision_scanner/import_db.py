#!/usr/bin/env python3
"""
Import Bitcoin addresses into SQLite database with indexing for fast lookups.
"""

import os
import sys
import sqlite3
import time
from datetime import datetime


DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "addresses.txt")
DB_FILE = os.path.join(DATA_DIR, "addresses.db")


def create_database():
    """Create SQLite database with optimized schema."""
    print("Creating database schema...")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create addresses table with index
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE
        )
    """)

    # Create index for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_address ON addresses(address)
    """)

    # Metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()

    print("✓ Database schema created")


def import_addresses():
    """Import addresses from text file into database."""

    if not os.path.exists(INPUT_FILE):
        print(f"✗ Error: {INPUT_FILE} not found")
        print(f"\nRun 'python3 download_addresses.py' first")
        return False

    print(f"Importing addresses from {INPUT_FILE}...")

    # Check file size
    file_size = os.path.getsize(INPUT_FILE)
    print(f"File size: {file_size / (1024*1024):.2f} MB")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Optimize SQLite for bulk insert
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")
    cursor.execute("PRAGMA cache_size = 1000000")  # 1GB cache

    start_time = time.time()
    count = 0
    batch = []
    batch_size = 10000

    print("\nImporting addresses...")

    try:
        with open(INPUT_FILE, 'r') as f:
            for line in f:
                address = line.strip()

                # Validate address (basic check)
                if not address or len(address) < 26:
                    continue

                batch.append((address,))
                count += 1

                # Insert in batches
                if len(batch) >= batch_size:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO addresses (address) VALUES (?)",
                        batch
                    )
                    conn.commit()
                    batch = []

                    # Progress update
                    elapsed = time.time() - start_time
                    rate = count / elapsed if elapsed > 0 else 0
                    print(f"  Imported: {count:,} addresses ({rate:,.0f}/sec)", end='\r')

            # Insert remaining addresses
            if batch:
                cursor.executemany(
                    "INSERT OR IGNORE INTO addresses (address) VALUES (?)",
                    batch
                )
                conn.commit()

    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        conn.close()
        return False

    # Final stats
    elapsed = time.time() - start_time
    print(f"\n\n✓ Import complete!")
    print(f"  Total addresses: {count:,}")
    print(f"  Time elapsed: {elapsed:.1f} seconds")
    print(f"  Average rate: {count/elapsed:,.0f} addresses/sec")

    # Store metadata
    cursor.execute("""
        INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)
    """, ("import_date", datetime.now().isoformat()))

    cursor.execute("""
        INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)
    """, ("total_addresses", str(count)))

    conn.commit()

    # Optimize database
    print("\nOptimizing database...")
    cursor.execute("ANALYZE")
    cursor.execute("VACUUM")

    conn.close()

    # Show final database size
    db_size = os.path.getsize(DB_FILE)
    print(f"✓ Database optimized")
    print(f"  Database size: {db_size / (1024*1024):.2f} MB")

    return True


def test_lookups():
    """Test database lookup performance."""
    print("\nTesting lookup performance...")

    if not os.path.exists(DB_FILE):
        print("✗ Database not found")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get a sample address
    cursor.execute("SELECT address FROM addresses LIMIT 1")
    result = cursor.fetchone()

    if not result:
        print("✗ No addresses in database")
        conn.close()
        return

    test_address = result[0]

    # Time lookups
    iterations = 10000
    start_time = time.time()

    for i in range(iterations):
        cursor.execute("SELECT 1 FROM addresses WHERE address = ? LIMIT 1", (test_address,))
        cursor.fetchone()

    elapsed = time.time() - start_time
    rate = iterations / elapsed

    print(f"✓ Lookup performance:")
    print(f"  {iterations:,} lookups in {elapsed:.2f} seconds")
    print(f"  Rate: {rate:,.0f} lookups/second")

    conn.close()


def show_stats():
    """Display database statistics."""
    if not os.path.exists(DB_FILE):
        print("✗ Database not found")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)

    # Get count
    cursor.execute("SELECT COUNT(*) FROM addresses")
    count = cursor.fetchone()[0]

    # Get metadata
    cursor.execute("SELECT value FROM metadata WHERE key = 'import_date'")
    import_date = cursor.fetchone()

    # Get sample addresses
    cursor.execute("SELECT address FROM addresses LIMIT 5")
    samples = cursor.fetchall()

    print(f"Total Addresses: {count:,}")
    if import_date:
        print(f"Import Date: {import_date[0]}")
    print(f"Database Size: {os.path.getsize(DB_FILE) / (1024*1024):.2f} MB")

    print(f"\nSample addresses:")
    for addr in samples:
        print(f"  {addr[0]}")

    print("="*70)

    conn.close()


def main():
    """Main entry point."""
    print("="*70)
    print("Bitcoin Address Database Importer")
    print("="*70)
    print()

    # Create database
    create_database()

    # Import addresses
    success = import_addresses()

    if not success:
        return

    # Test performance
    test_lookups()

    # Show stats
    show_stats()

    print("\n✓ Database ready!")
    print("\nNext step: python3 scanner.py")


if __name__ == "__main__":
    main()
