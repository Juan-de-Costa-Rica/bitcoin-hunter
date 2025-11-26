#!/usr/bin/env python3
"""
Bitcoin Address Hunter - Main Scanner

Generates random Bitcoin private keys and checks if the derived addresses
exist in the local database of funded addresses.

Educational demonstration of Bitcoin's keyspace security.
"""

import os
import sys
import sqlite3
import time
import signal
from datetime import datetime, timedelta
from bitcoin_utils import generate_private_key, generate_all_addresses


# Configuration
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "addresses.db")
LOG_FILE = "logs/found.txt"
STATS_INTERVAL = 1.0  # Update stats every second


class Scanner:
    """Bitcoin address scanner."""

    def __init__(self):
        self.db_conn = None
        self.db_cursor = None
        self.total_keys = 0
        self.total_addresses = 0
        self.found_count = 0
        self.start_time = None
        self.last_stats_time = None
        self.running = True

        # Stats tracking
        self.keys_since_last_update = 0
        self.addresses_since_last_update = 0

    def connect_db(self):
        """Connect to address database."""
        if not os.path.exists(DB_FILE):
            print(f"✗ Error: Database not found at {DB_FILE}")
            print("\nRun these commands first:")
            print("  1. python3 download_addresses.py")
            print("  2. python3 import_db.py")
            sys.exit(1)

        print("Connecting to database...")
        self.db_conn = sqlite3.connect(DB_FILE)
        self.db_cursor = self.db_conn.cursor()

        # Get database stats
        self.db_cursor.execute("SELECT COUNT(*) FROM addresses")
        db_count = self.db_cursor.fetchone()[0]
        print(f"✓ Database loaded: {db_count:,} addresses")

        return db_count

    def check_address(self, address):
        """Check if address exists in database."""
        self.db_cursor.execute(
            "SELECT 1 FROM addresses WHERE address = ? LIMIT 1",
            (address,)
        )
        return self.db_cursor.fetchone() is not None

    def log_found(self, key_data):
        """Log found addresses to file."""
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        with open(LOG_FILE, 'a') as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"FOUND AT: {datetime.now().isoformat()}\n")
            f.write(f"{'='*70}\n")
            f.write(f"Private Key (hex): {key_data['private_key_hex']}\n")
            f.write(f"Private Key (WIF): {key_data['private_key_wif']}\n")
            f.write(f"Public Key: {key_data['public_key_hex']}\n")
            f.write(f"\nAddresses:\n")
            f.write(f"  P2PKH (compressed):   {key_data['p2pkh_compressed']}\n")
            f.write(f"  P2PKH (uncompressed): {key_data['p2pkh_uncompressed']}\n")
            f.write(f"  P2WPKH (bech32):      {key_data['p2wpkh_bech32']}\n")
            f.write(f"\nFound address: {key_data['found_address']}\n")
            f.write(f"{'='*70}\n")

    def display_stats(self, force=False):
        """Display scanning statistics."""
        now = time.time()

        # Only update at specified interval (unless forced)
        if not force and self.last_stats_time:
            if now - self.last_stats_time < STATS_INTERVAL:
                return

        elapsed = now - self.start_time
        interval = now - (self.last_stats_time or self.start_time)

        # Calculate rates
        overall_keys_rate = self.total_keys / elapsed if elapsed > 0 else 0
        overall_addr_rate = self.total_addresses / elapsed if elapsed > 0 else 0

        current_keys_rate = self.keys_since_last_update / interval if interval > 0 else 0
        current_addr_rate = self.addresses_since_last_update / interval if interval > 0 else 0

        # Format elapsed time
        elapsed_td = timedelta(seconds=int(elapsed))

        # Clear line and display stats
        print(f"\r{' ' * 120}\r", end='')  # Clear line
        print(
            f"Keys: {self.total_keys:,} | "
            f"Addresses: {self.total_addresses:,} | "
            f"Rate: {current_keys_rate:,.0f} k/s, {current_addr_rate:,.0f} a/s | "
            f"Found: {self.found_count} | "
            f"Time: {elapsed_td}",
            end='',
            flush=True
        )

        # Reset interval counters
        self.keys_since_last_update = 0
        self.addresses_since_last_update = 0
        self.last_stats_time = now

    def scan_loop(self):
        """Main scanning loop."""
        print("\n" + "="*70)
        print("Starting scan... (Press Ctrl+C to stop)")
        print("="*70)
        print()

        self.start_time = time.time()
        self.last_stats_time = self.start_time

        try:
            while self.running:
                # Generate random private key
                private_key = generate_private_key()

                # Generate all addresses
                addresses = generate_all_addresses(private_key)

                # Update counters
                self.total_keys += 1
                self.keys_since_last_update += 1

                # Check each address type
                address_list = [
                    addresses['p2pkh_compressed'],
                    addresses['p2pkh_uncompressed'],
                    addresses['p2wpkh_bech32'],
                ]

                for addr in address_list:
                    self.total_addresses += 1
                    self.addresses_since_last_update += 1

                    if self.check_address(addr):
                        # FOUND!
                        self.found_count += 1

                        # Display alert
                        print(f"\n\n{'*' * 70}")
                        print(f"*** FOUND FUNDED ADDRESS! ***")
                        print(f"{'*' * 70}")
                        print(f"Address: {addr}")
                        print(f"Private Key (WIF): {addresses['private_key_wif']}")
                        print(f"{'*' * 70}\n")

                        # Log to file
                        addresses['private_key_hex'] = private_key.hex()
                        addresses['found_address'] = addr
                        self.log_found(addresses)

                        print(f"Details saved to: {LOG_FILE}\n")

                # Update stats display
                self.display_stats()

        except KeyboardInterrupt:
            print("\n\nStopping scanner...")
            self.running = False

        # Final stats
        self.display_stats(force=True)
        print("\n\n" + "="*70)
        print("FINAL STATISTICS")
        print("="*70)

        elapsed = time.time() - self.start_time
        print(f"Total Keys Generated: {self.total_keys:,}")
        print(f"Total Addresses Checked: {self.total_addresses:,}")
        print(f"Addresses Found: {self.found_count}")
        print(f"Total Runtime: {timedelta(seconds=int(elapsed))}")
        print(f"Average Rate: {self.total_keys/elapsed:,.0f} keys/sec")
        print("="*70)

    def run(self):
        """Run the scanner."""
        print("="*70)
        print("Bitcoin Address Hunter")
        print("="*70)
        print()
        print("This scanner demonstrates Bitcoin's keyspace security by randomly")
        print("generating private keys and checking if the addresses have funds.")
        print()
        print("Reality check:")
        print("  There are ~1.4 × 10^48 possible Bitcoin addresses.")
        print("  The probability of finding a funded address randomly is")
        print("  essentially ZERO (1 in 29 duodecillion).")
        print()
        print("This is an EDUCATIONAL project showing why Bitcoin is secure!")
        print()

        # Connect to database
        db_count = self.connect_db()

        # Show odds
        print()
        print(f"Your chances of finding a funded address:")
        print(f"  1 in {(2**160) / db_count:.2e}")
        print()

        input("Press Enter to start scanning...")

        # Start scanning
        self.scan_loop()

        # Cleanup
        if self.db_conn:
            self.db_conn.close()


def main():
    """Main entry point."""
    scanner = Scanner()
    scanner.run()


if __name__ == "__main__":
    main()
