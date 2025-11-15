#!/usr/bin/env python3
"""
Bitcoin Address Hunter - Multi-Core Scanner

Uses all available CPU cores for maximum performance.
Production-ready with full error handling and monitoring.
"""

import os
import sys
import sqlite3
import time
import signal
import logging
import multiprocessing
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from bitcoin_utils import generate_private_key, generate_all_addresses


# Configuration
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "addresses.db")
FOUND_LOG = "logs/found.txt"
STATS_LOG = "logs/stats.log"
ERROR_LOG = "logs/errors.log"
STATS_INTERVAL = 1.0
LOG_STATS_INTERVAL = 60
DB_HEALTH_CHECK_INTERVAL = 300


def setup_logging(worker_id=None):
    """Configure logging with rotation."""
    os.makedirs("logs", exist_ok=True)

    logger_name = f'scanner.worker{worker_id}' if worker_id is not None else 'scanner'
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter('%(asctime)s - %(message)s')

    # Console handler (main process only)
    if worker_id is None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    # File handlers
    error_handler = RotatingFileHandler(
        ERROR_LOG, maxBytes=10*1024*1024, backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)

    stats_handler = RotatingFileHandler(
        STATS_LOG, maxBytes=50*1024*1024, backupCount=3
    )
    stats_handler.setLevel(logging.INFO)
    stats_handler.setFormatter(simple_formatter)
    logger.addHandler(stats_handler)

    return logger


class WorkerProcess:
    """Individual worker process for scanning."""

    def __init__(self, worker_id, stats_queue, stop_event):
        self.worker_id = worker_id
        self.stats_queue = stats_queue
        self.stop_event = stop_event
        self.logger = None
        self.db_conn = None
        self.db_cursor = None

        self.total_keys = 0
        self.total_addresses = 0
        self.found_count = 0
        self.error_count = 0
        self.last_db_check = None

    def connect_db(self):
        """Connect to database."""
        try:
            if not os.path.exists(DB_FILE):
                self.logger.error(f"Worker {self.worker_id}: Database not found")
                return False

            self.db_conn = sqlite3.connect(DB_FILE, timeout=30.0)
            self.db_conn.row_factory = sqlite3.Row
            self.db_cursor = self.db_conn.cursor()
            self.last_db_check = time.time()

            return True

        except Exception as e:
            self.logger.error(f"Worker {self.worker_id}: DB connection failed: {e}")
            return False

    def check_db_health(self):
        """Check database health and reconnect if needed."""
        try:
            self.db_cursor.execute("SELECT 1")
            self.db_cursor.fetchone()
            return True
        except:
            self.logger.warning(f"Worker {self.worker_id}: DB health check failed, reconnecting")
            try:
                if self.db_conn:
                    self.db_conn.close()
            except:
                pass
            return self.connect_db()

    def check_address(self, address):
        """Check if address exists in database."""
        try:
            self.db_cursor.execute(
                "SELECT 1 FROM addresses WHERE address = ? LIMIT 1",
                (address,)
            )
            return self.db_cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"Worker {self.worker_id}: Query error: {e}")
            self.error_count += 1

            if self.check_db_health():
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
        """Log found address."""
        try:
            os.makedirs(os.path.dirname(FOUND_LOG), exist_ok=True)

            with open(FOUND_LOG, 'a') as f:
                f.write(f"\n{'='*70}\n")
                f.write(f"FOUND BY WORKER {self.worker_id} AT: {datetime.now().isoformat()}\n")
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

        except Exception as e:
            self.logger.error(f"Worker {self.worker_id}: Failed to log found address: {e}")
            self.logger.critical(f"FOUND: {key_data['found_address']} - {key_data['private_key_wif']}")

    def run(self):
        """Main worker loop."""
        self.logger = setup_logging(self.worker_id)
        self.logger.info(f"Worker {self.worker_id} starting")

        if not self.connect_db():
            self.logger.error(f"Worker {self.worker_id} failed to connect to database")
            return

        consecutive_errors = 0
        max_consecutive_errors = 100
        last_stats_report = time.time()

        while not self.stop_event.is_set():
            try:
                # Periodic DB health check
                now = time.time()
                if (now - self.last_db_check) >= DB_HEALTH_CHECK_INTERVAL:
                    if not self.check_db_health():
                        self.logger.error(f"Worker {self.worker_id}: DB health check failed")
                        break
                    self.last_db_check = now

                # Generate key and addresses
                try:
                    private_key = generate_private_key()
                    addresses = generate_all_addresses(private_key)
                except Exception as e:
                    self.logger.error(f"Worker {self.worker_id}: Key generation error: {e}")
                    self.error_count += 1
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    time.sleep(0.1)
                    continue

                consecutive_errors = 0
                self.total_keys += 1

                # Check addresses
                address_list = [
                    addresses['p2pkh_compressed'],
                    addresses['p2pkh_uncompressed'],
                    addresses['p2wpkh_bech32'],
                ]

                for addr in address_list:
                    self.total_addresses += 1

                    if self.check_address(addr):
                        self.found_count += 1
                        self.logger.critical(f"Worker {self.worker_id} FOUND: {addr}")

                        addresses['private_key_hex'] = private_key.hex()
                        addresses['found_address'] = addr
                        self.log_found(addresses)

                # Report stats to main process every second
                if (now - last_stats_report) >= 1.0:
                    self.stats_queue.put({
                        'worker_id': self.worker_id,
                        'keys': self.total_keys,
                        'addresses': self.total_addresses,
                        'found': self.found_count,
                        'errors': self.error_count
                    })
                    last_stats_report = now

            except Exception as e:
                self.logger.error(f"Worker {self.worker_id}: Unexpected error: {e}")
                self.error_count += 1
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
                time.sleep(0.1)

        # Final stats report
        self.stats_queue.put({
            'worker_id': self.worker_id,
            'keys': self.total_keys,
            'addresses': self.total_addresses,
            'found': self.found_count,
            'errors': self.error_count,
            'final': True
        })

        if self.db_conn:
            self.db_conn.close()

        self.logger.info(f"Worker {self.worker_id} stopped - {self.total_keys:,} keys, {self.found_count} found")


class MultiCoreScanner:
    """Main scanner coordinator using multiple CPU cores."""

    def __init__(self, num_workers=None):
        self.num_workers = num_workers or multiprocessing.cpu_count()
        self.logger = setup_logging()
        self.stats_queue = multiprocessing.Queue()
        self.stop_event = multiprocessing.Event()
        self.workers = []

        self.worker_stats = {}
        self.start_time = None
        self.last_log_time = None

        # Signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        try:
            signal.signal(signal.SIGHUP, self._signal_handler)
        except AttributeError:
            pass

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, shutting down workers...")
        self.stop_event.set()

    def start_workers(self):
        """Start all worker processes."""
        self.logger.info(f"Starting {self.num_workers} worker processes...")

        for i in range(self.num_workers):
            worker = WorkerProcess(i, self.stats_queue, self.stop_event)
            process = multiprocessing.Process(target=worker.run, name=f"Worker-{i}")
            process.start()
            self.workers.append(process)
            self.worker_stats[i] = {'keys': 0, 'addresses': 0, 'found': 0, 'errors': 0}

        self.logger.info(f"All {self.num_workers} workers started")

    def monitor_workers(self):
        """Monitor worker stats and display progress."""
        self.start_time = time.time()
        self.last_log_time = self.start_time
        last_display_time = self.start_time

        self.logger.info("="*70)
        self.logger.info("Multi-Core Scanner Running (Press Ctrl+C to stop)")
        self.logger.info("="*70)

        while any(w.is_alive() for w in self.workers):
            try:
                # Collect stats from workers (non-blocking)
                while not self.stats_queue.empty():
                    stat = self.stats_queue.get_nowait()
                    worker_id = stat['worker_id']

                    self.worker_stats[worker_id] = {
                        'keys': stat['keys'],
                        'addresses': stat['addresses'],
                        'found': stat['found'],
                        'errors': stat['errors']
                    }

                # Calculate totals
                now = time.time()
                total_keys = sum(w['keys'] for w in self.worker_stats.values())
                total_addresses = sum(w['addresses'] for w in self.worker_stats.values())
                total_found = sum(w['found'] for w in self.worker_stats.values())
                total_errors = sum(w['errors'] for w in self.worker_stats.values())

                elapsed = now - self.start_time
                rate = total_keys / elapsed if elapsed > 0 else 0

                # Display stats every second
                if (now - last_display_time) >= STATS_INTERVAL:
                    print(f"\r{' ' * 120}\r", end='')
                    print(
                        f"Workers: {self.num_workers} | "
                        f"Keys: {total_keys:,} | "
                        f"Addresses: {total_addresses:,} | "
                        f"Rate: {rate:,.0f} k/s | "
                        f"Found: {total_found} | "
                        f"Errors: {total_errors} | "
                        f"Time: {timedelta(seconds=int(elapsed))}",
                        end='',
                        flush=True
                    )
                    last_display_time = now

                # Log stats to file every minute
                if (now - self.last_log_time) >= LOG_STATS_INTERVAL:
                    self.logger.info(
                        f"Stats: {total_keys:,} keys, {total_addresses:,} addrs, "
                        f"{rate:,.0f} k/s avg, {total_found} found, {total_errors} errors"
                    )
                    self.last_log_time = now

                time.sleep(0.1)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop_event.set()
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")

        # Wait for workers to finish
        for w in self.workers:
            w.join(timeout=5)
            if w.is_alive():
                w.terminate()

        # Final stats
        print("\n\n" + "="*70)
        print("FINAL STATISTICS")
        print("="*70)

        total_keys = sum(w['keys'] for w in self.worker_stats.values())
        total_addresses = sum(w['addresses'] for w in self.worker_stats.values())
        total_found = sum(w['found'] for w in self.worker_stats.values())
        total_errors = sum(w['errors'] for w in self.worker_stats.values())
        elapsed = time.time() - self.start_time
        avg_rate = total_keys / elapsed if elapsed > 0 else 0

        print(f"Workers Used: {self.num_workers}")
        print(f"Total Keys Generated: {total_keys:,}")
        print(f"Total Addresses Checked: {total_addresses:,}")
        print(f"Addresses Found: {total_found}")
        print(f"Errors Encountered: {total_errors}")
        print(f"Total Runtime: {timedelta(seconds=int(elapsed))}")
        print(f"Average Rate: {avg_rate:,.0f} keys/sec")
        print(f"Per-Core Rate: {avg_rate/self.num_workers:,.0f} keys/sec")
        print("="*70)

        self.logger.info("="*70)
        self.logger.info(f"Multi-core scanner stopped - {self.num_workers} workers")
        self.logger.info(f"Total: {total_keys:,} keys, {total_found} found, {total_errors} errors")
        self.logger.info(f"Average rate: {avg_rate:,.0f} keys/sec")
        self.logger.info("="*70)

    def run(self):
        """Run the multi-core scanner."""
        self.logger.info("="*70)
        self.logger.info("Bitcoin Address Hunter - Multi-Core Scanner")
        self.logger.info("="*70)
        self.logger.info(f"CPU cores available: {multiprocessing.cpu_count()}")
        self.logger.info(f"Using {self.num_workers} worker processes")

        # Check database exists
        if not os.path.exists(DB_FILE):
            self.logger.error(f"Database not found at {DB_FILE}")
            self.logger.error("Run: python3 download_blockchair.py && python3 import_db.py")
            return 1

        # Get DB info
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM addresses")
            db_count = cursor.fetchone()[0]
            conn.close()

            self.logger.info(f"Database: {db_count:,} addresses")
            probability = db_count / (2**160)
            expected = int(1 / probability) if probability > 0 else 0
            self.logger.info(f"Probability: 1 in {expected:.2e}")
        except Exception as e:
            self.logger.error(f"Could not read database: {e}")

        time.sleep(2)

        # Start workers and monitor
        self.start_workers()
        self.monitor_workers()

        return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Multi-core Bitcoin address scanner')
    parser.add_argument('-w', '--workers', type=int, help='Number of worker processes (default: CPU count)')
    args = parser.parse_args()

    logger = setup_logging()
    logger.info("Starting Multi-Core Bitcoin Address Hunter")
    logger.info(f"PID: {os.getpid()}")

    scanner = MultiCoreScanner(num_workers=args.workers)
    exit_code = scanner.run()

    logger.info(f"Scanner exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
