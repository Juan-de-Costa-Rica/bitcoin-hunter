#!/usr/bin/env python3
"""
Bitcoin Address Hunter - Production Daemon

Hardened version for 24/7 autonomous operation.
- No user input required
- Comprehensive error handling
- Automatic database reconnection
- Signal handling for graceful shutdown
- Rotating log files
- Performance metrics logging
"""

import os
import sys
import sqlite3
import time
import signal
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from bitcoin_utils import generate_private_key, generate_all_addresses


# Configuration
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "addresses.db")
FOUND_LOG = "logs/found.txt"
STATS_LOG = "logs/stats.log"
ERROR_LOG = "logs/errors.log"
STATS_INTERVAL = 1.0  # Update stats every second
LOG_STATS_INTERVAL = 60  # Log stats to file every 60 seconds
DB_HEALTH_CHECK_INTERVAL = 300  # Check DB health every 5 minutes


def setup_logging():
    """Configure logging with rotation."""
    os.makedirs("logs", exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter('%(asctime)s - %(message)s')

    # Main logger
    logger = logging.getLogger('scanner')
    logger.setLevel(logging.INFO)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler for errors (rotating, 10MB max, keep 5 files)
    error_handler = RotatingFileHandler(
        ERROR_LOG, maxBytes=10*1024*1024, backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)

    # File handler for stats (rotating, 50MB max, keep 3 files)
    stats_handler = RotatingFileHandler(
        STATS_LOG, maxBytes=50*1024*1024, backupCount=3
    )
    stats_handler.setLevel(logging.INFO)
    stats_handler.setFormatter(simple_formatter)
    logger.addHandler(stats_handler)

    return logger


class Scanner:
    """Production-ready Bitcoin address scanner."""

    def __init__(self, logger):
        self.logger = logger
        self.db_conn = None
        self.db_cursor = None
        self.total_keys = 0
        self.total_addresses = 0
        self.found_count = 0
        self.error_count = 0
        self.start_time = None
        self.last_stats_time = None
        self.last_log_time = None
        self.last_db_check = None
        self.running = True

        # Stats tracking
        self.keys_since_last_update = 0
        self.addresses_since_last_update = 0

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        try:
            signal.signal(signal.SIGHUP, self._signal_handler)
        except AttributeError:
            # SIGHUP not available on Windows
            pass

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, shutting down gracefully...")
        self.running = False

    def connect_db(self):
        """Connect to address database with error handling."""
        try:
            if not os.path.exists(DB_FILE):
                self.logger.error(f"Database not found at {DB_FILE}")
                self.logger.error("Run: python3 download_blockchair.py && python3 import_db.py")
                return False

            self.logger.info("Connecting to database...")
            self.db_conn = sqlite3.connect(DB_FILE, timeout=30.0)
            self.db_conn.row_factory = sqlite3.Row
            self.db_cursor = self.db_conn.cursor()

            # Get database stats
            self.db_cursor.execute("SELECT COUNT(*) as count FROM addresses")
            db_count = self.db_cursor.fetchone()['count']
            self.logger.info(f"Database loaded: {db_count:,} addresses")

            self.last_db_check = time.time()
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to database: {e}")
            return False

    def check_db_health(self):
        """Verify database connection is healthy, reconnect if needed."""
        try:
            # Simple query to check connection
            self.db_cursor.execute("SELECT 1")
            self.db_cursor.fetchone()
            return True
        except sqlite3.Error as e:
            self.logger.warning(f"Database health check failed: {e}")
            self.logger.info("Attempting to reconnect...")

            # Close old connection
            try:
                if self.db_conn:
                    self.db_conn.close()
            except:
                pass

            # Reconnect
            return self.connect_db()

    def check_address(self, address):
        """Check if address exists in database with error handling."""
        try:
            self.db_cursor.execute(
                "SELECT 1 FROM addresses WHERE address = ? LIMIT 1",
                (address,)
            )
            return self.db_cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"Database query error for {address}: {e}")
            self.error_count += 1

            # Try to reconnect
            if self.check_db_health():
                # Retry query once
                try:
                    self.db_cursor.execute(
                        "SELECT 1 FROM addresses WHERE address = ? LIMIT 1",
                        (address,)
                    )
                    return self.db_cursor.fetchone() is not None
                except:
                    return False
            return False

    def log_found(self, key_data):
        """Log found addresses to file with error handling."""
        try:
            os.makedirs(os.path.dirname(FOUND_LOG), exist_ok=True)

            with open(FOUND_LOG, 'a') as f:
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

            self.logger.info(f"Found address logged to {FOUND_LOG}")

        except IOError as e:
            # File I/O failed - log to console as fallback
            self.logger.error(f"Failed to write found address to file: {e}")
            self.logger.critical("FOUND ADDRESS (file write failed, logging here):")
            self.logger.critical(f"  Address: {key_data['found_address']}")
            self.logger.critical(f"  Private Key (WIF): {key_data['private_key_wif']}")
            self.logger.critical(f"  Private Key (hex): {key_data['private_key_hex']}")
        except Exception as e:
            self.logger.error(f"Unexpected error logging found address: {e}")

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
        current_keys_rate = self.keys_since_last_update / interval if interval > 0 else 0
        current_addr_rate = self.addresses_since_last_update / interval if interval > 0 else 0

        # Format elapsed time
        elapsed_td = timedelta(seconds=int(elapsed))

        # Clear line and display stats
        print(f"\r{' ' * 120}\r", end='')
        print(
            f"Keys: {self.total_keys:,} | "
            f"Addresses: {self.total_addresses:,} | "
            f"Rate: {current_keys_rate:,.0f} k/s, {current_addr_rate:,.0f} a/s | "
            f"Found: {self.found_count} | "
            f"Errors: {self.error_count} | "
            f"Time: {elapsed_td}",
            end='',
            flush=True
        )

        # Reset interval counters
        self.keys_since_last_update = 0
        self.addresses_since_last_update = 0
        self.last_stats_time = now

        # Log stats to file periodically
        if not self.last_log_time or (now - self.last_log_time) >= LOG_STATS_INTERVAL:
            overall_rate = self.total_keys / elapsed if elapsed > 0 else 0
            self.logger.info(
                f"Stats: {self.total_keys:,} keys, "
                f"{self.total_addresses:,} addrs, "
                f"{overall_rate:,.0f} k/s avg, "
                f"{self.found_count} found, "
                f"{self.error_count} errors"
            )
            self.last_log_time = now

    def scan_loop(self):
        """Main scanning loop with comprehensive error handling."""
        self.logger.info("="*70)
        self.logger.info("Starting scan... (Send SIGTERM or SIGINT to stop)")
        self.logger.info("="*70)

        self.start_time = time.time()
        self.last_stats_time = self.start_time
        self.last_log_time = self.start_time

        consecutive_errors = 0
        max_consecutive_errors = 100

        while self.running:
            try:
                # Periodic database health check
                now = time.time()
                if (now - self.last_db_check) >= DB_HEALTH_CHECK_INTERVAL:
                    if not self.check_db_health():
                        self.logger.error("Database health check failed, stopping scanner")
                        break
                    self.last_db_check = now

                # Generate random private key
                try:
                    private_key = generate_private_key()
                except Exception as e:
                    self.logger.error(f"Private key generation failed: {e}")
                    self.error_count += 1
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.critical("Too many consecutive errors, stopping")
                        break
                    time.sleep(0.1)  # Brief pause before retry
                    continue

                # Generate all addresses
                try:
                    addresses = generate_all_addresses(private_key)
                except Exception as e:
                    self.logger.error(f"Address generation failed: {e}")
                    self.error_count += 1
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.critical("Too many consecutive errors, stopping")
                        break
                    time.sleep(0.1)
                    continue

                # Reset consecutive error counter on success
                consecutive_errors = 0

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

                        self.logger.critical(f"FOUND: {addr}")

                        # Log to file
                        addresses['private_key_hex'] = private_key.hex()
                        addresses['found_address'] = addr
                        self.log_found(addresses)

                # Update stats display
                self.display_stats()

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                self.error_count += 1
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.critical("Too many consecutive errors, stopping")
                    break
                time.sleep(0.1)

        # Final stats
        self.display_stats(force=True)
        print("\n\n" + "="*70)
        print("FINAL STATISTICS")
        print("="*70)

        elapsed = time.time() - self.start_time
        avg_rate = self.total_keys / elapsed if elapsed > 0 else 0

        print(f"Total Keys Generated: {self.total_keys:,}")
        print(f"Total Addresses Checked: {self.total_addresses:,}")
        print(f"Addresses Found: {self.found_count}")
        print(f"Errors Encountered: {self.error_count}")
        print(f"Total Runtime: {timedelta(seconds=int(elapsed))}")
        print(f"Average Rate: {avg_rate:,.0f} keys/sec")
        print("="*70)

        self.logger.info("="*70)
        self.logger.info(f"Scanner stopped - Runtime: {timedelta(seconds=int(elapsed))}")
        self.logger.info(f"Total: {self.total_keys:,} keys, {self.found_count} found, {self.error_count} errors")
        self.logger.info("="*70)

    def run(self):
        """Run the scanner daemon."""
        self.logger.info("="*70)
        self.logger.info("Bitcoin Address Hunter - Production Daemon")
        self.logger.info("="*70)

        # Connect to database
        if not self.connect_db():
            self.logger.error("Failed to connect to database, exiting")
            return 1

        # Get database info for probability calculation
        try:
            self.db_cursor.execute("SELECT COUNT(*) as count FROM addresses")
            db_count = self.db_cursor.fetchone()['count']

            probability = db_count / (2**160)
            expected_checks = int(1 / probability) if probability > 0 else 0

            self.logger.info(f"Database contains {db_count:,} addresses")
            self.logger.info(f"Probability of finding one: 1 in {expected_checks:.2e}")
            self.logger.info("Starting autonomous scanning...")

        except Exception as e:
            self.logger.warning(f"Could not calculate probability: {e}")

        # Start scanning (no user input required)
        time.sleep(2)  # Brief pause to read messages
        self.scan_loop()

        # Cleanup
        try:
            if self.db_conn:
                self.db_conn.close()
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")

        return 0


def main():
    """Main entry point."""
    # Setup logging
    logger = setup_logging()

    logger.info("Starting Bitcoin Address Hunter Daemon")
    logger.info(f"PID: {os.getpid()}")

    # Run scanner
    scanner = Scanner(logger)
    exit_code = scanner.run()

    logger.info(f"Daemon exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
