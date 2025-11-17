#!/usr/bin/env python3
"""
Bitcoin Puzzle Solver - CPU Optimized Incremental Search

Optimized for ARM64 CPU execution. Uses multi-core processing,
checkpointing, and efficient key generation.

This approach is more practical than Kangaroo for CPU-only hardware.
"""

import os
import sys
import time
import json
import signal
import hashlib
import multiprocessing
import logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from datetime import datetime, timedelta
import ecdsa
from ecdsa import SECP256k1, SigningKey
from ecdsa.util import sigencode_string
import base58


# Bitcoin secp256k1 parameters
CURVE = SECP256k1
G = CURVE.generator


@dataclass
class PuzzleConfig:
    """Configuration for a specific puzzle."""
    puzzle_num: int
    range_min: int
    range_max: int
    target_pubkey_hex: str
    prize_btc: float
    status: str


# Known Bitcoin puzzles
PUZZLES = {
    10: PuzzleConfig(
        puzzle_num=10,
        range_min=2**9,
        range_max=2**10,
        target_pubkey_hex="0209c58240e50e3ba3f833c82655e8725c037a2294e14cf5d73a5df8d56159de69",
        prize_btc=0.001,
        status="SOLVED - Testing only"
    ),
    71: PuzzleConfig(
        puzzle_num=71,
        range_min=2**70,
        range_max=2**71,
        target_pubkey_hex="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU",  # Address, not pubkey
        prize_btc=7.1,
        status="UNSOLVED - $426k prize"
    ),
    20: PuzzleConfig(
        puzzle_num=20,
        range_min=2**19,
        range_max=2**20,
        target_pubkey_hex="0309976ba5570966bf889196b7fdf5a0f9a1e9ab340556ec29f8bb60599616167d",
        prize_btc=0.02,
        status="SOLVED - Testing only"
    ),
    30: PuzzleConfig(
        puzzle_num=30,
        range_min=2**29,
        range_max=2**30,
        target_pubkey_hex="0248b3c90c07c8d9cba0d1e69c84c5d8f4f729d67e6fd4a4e12275b209d04c5ccd",
        prize_btc=0.03,
        status="SOLVED - Testing only"
    ),
    66: PuzzleConfig(
        puzzle_num=66,
        range_min=2**65,
        range_max=2**66,
        target_pubkey_hex="03a2efa402fd5268400c77c20e574ba86409ededee7c4020e4b9f0edbee53de0d4",
        prize_btc=6.6,
        status="UNSOLVED - $400k+ prize"
    ),
}


class PuzzleSearcher:
    """Multi-core incremental search for Bitcoin puzzles."""

    def __init__(self, config: PuzzleConfig, workers: int = None, checkpoint_file: str = None):
        self.config = config
        self.workers = workers or multiprocessing.cpu_count()
        self.checkpoint_file = checkpoint_file or f"puzzle_{config.puzzle_num}_checkpoint.json"

        # Setup logging
        os.makedirs("logs", exist_ok=True)
        self.logger = logging.getLogger(f'puzzle{config.puzzle_num}')
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            f'logs/puzzle{config.puzzle_num}.log',
            maxBytes=50*1024*1024,
            backupCount=3
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Error handler
        error_handler = RotatingFileHandler(
            f'logs/puzzle{config.puzzle_num}_errors.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)

        # Determine if target is address or pubkey
        if config.target_pubkey_hex.startswith('1') or config.target_pubkey_hex.startswith('3') or config.target_pubkey_hex.startswith('bc1'):
            self.target_type = 'address'
            self.target_address = config.target_pubkey_hex
            self.target_point = None
        else:
            self.target_type = 'pubkey'
            self.target_point = self._hex_to_point(config.target_pubkey_hex)
            self.target_address = None

        self.range_size = config.range_max - config.range_min

        # Load checkpoint if exists
        self.start_key = self._load_checkpoint()

        self.stop_event = multiprocessing.Event()
        self.result_queue = multiprocessing.Queue()
        self.stats_queue = multiprocessing.Queue()

        # Signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _hex_to_point(self, hex_pubkey: str):
        """Convert hex public key to EC point."""
        pubkey_bytes = bytes.fromhex(hex_pubkey)

        if len(pubkey_bytes) == 33:
            # Compressed
            x = int.from_bytes(pubkey_bytes[1:33], 'big')
            y_parity = pubkey_bytes[0] - 0x02

            # Calculate y from x
            y_squared = (pow(x, 3, CURVE.curve.p()) + CURVE.curve.b()) % CURVE.curve.p()
            y = pow(y_squared, (CURVE.curve.p() + 1) // 4, CURVE.curve.p())

            if y % 2 != y_parity:
                y = CURVE.curve.p() - y

            return (x, y)
        else:
            raise ValueError(f"Unsupported pubkey format")

    def _load_checkpoint(self) -> int:
        """Load progress from checkpoint file."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    last_key = data.get('last_key_checked', self.config.range_min)
                    print(f"Resuming from checkpoint: {last_key:,}")
                    print(f"Progress: {((last_key - self.config.range_min) / self.range_size * 100):.4f}%")
                    return last_key
            except:
                pass

        return self.config.range_min

    def _save_checkpoint(self, last_key: int, keys_checked: int, elapsed: float):
        """Save progress to checkpoint file."""
        try:
            data = {
                'puzzle_num': self.config.puzzle_num,
                'last_key_checked': last_key,
                'keys_checked': keys_checked,
                'elapsed_seconds': elapsed,
                'timestamp': datetime.now().isoformat(),
                'progress_percent': ((last_key - self.config.range_min) / self.range_size * 100)
            }

            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_event.set()

    def _private_key_to_address(self, private_key_bytes):
        """Convert private key to Bitcoin P2PKH address."""
        import hashlib
        import base58

        sk = SigningKey.from_string(private_key_bytes, curve=CURVE)
        vk = sk.get_verifying_key()

        # Get compressed public key
        pubkey_point = vk.pubkey.point
        x = pubkey_point.x()
        y = pubkey_point.y()

        # Compressed public key format
        if y % 2 == 0:
            pubkey_compressed = b'\x02' + x.to_bytes(32, 'big')
        else:
            pubkey_compressed = b'\x03' + x.to_bytes(32, 'big')

        # Hash160
        sha256_hash = hashlib.sha256(pubkey_compressed).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

        # Add version byte (0x00 for mainnet P2PKH)
        versioned = b'\x00' + ripemd160_hash

        # Checksum
        checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]

        # Encode
        address = base58.b58encode(versioned + checksum).decode('ascii')

        return address, (x, y)

    def _worker_process(self, worker_id: int, start_key: int, end_key: int):
        """Worker process to search a key range."""
        keys_checked = 0
        last_report = time.time()
        report_interval = 5.0

        current_key = start_key

        # Debug: check first key
        if worker_id == 0:
            print(f"Worker {worker_id}: Searching keys {start_key:,} to {end_key:,}")
            if self.target_type == 'address':
                print(f"Worker {worker_id}: Target address: {self.target_address}")
            else:
                print(f"Worker {worker_id}: Target point: x={self.target_point[0]}, y={self.target_point[1]}")

        while current_key < end_key and not self.stop_event.is_set():
            try:
                # Generate address and pubkey for current private key
                private_key_bytes = current_key.to_bytes(32, 'big')
                address, (x, y) = self._private_key_to_address(private_key_bytes)

                # Debug: print first few keys
                if worker_id == 0 and keys_checked < 3:
                    if self.target_type == 'address':
                        print(f"Worker {worker_id}: Key {current_key} -> address {address}")
                    else:
                        print(f"Worker {worker_id}: Key {current_key} -> point x={x}")

                # Check if this matches target
                match_found = False
                if self.target_type == 'address':
                    if address == self.target_address:
                        match_found = True
                else:
                    if x == self.target_point[0] and y == self.target_point[1]:
                        match_found = True

                if match_found:
                    # FOUND!
                    print(f"\nWorker {worker_id}: MATCH at key {current_key}!")
                    self.result_queue.put({
                        'found': True,
                        'private_key': current_key,
                        'worker_id': worker_id,
                        'address': address
                    })
                    return

                current_key += 1
                keys_checked += 1

                # Report progress
                if time.time() - last_report >= report_interval:
                    self.stats_queue.put({
                        'worker_id': worker_id,
                        'keys_checked': keys_checked,
                        'current_key': current_key
                    })
                    keys_checked = 0
                    last_report = time.time()

            except Exception as e:
                print(f"\nWorker {worker_id} error at key {current_key}: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)

        # Final stats
        print(f"\nWorker {worker_id}: Exiting. Checked {keys_checked} keys from {start_key} to {current_key}")
        self.stats_queue.put({
            'worker_id': worker_id,
            'keys_checked': keys_checked,
            'current_key': current_key,
            'final': True
        })

    def search(self):
        """Run the multi-core search."""
        print("="*70)
        print(f"Bitcoin Puzzle #{self.config.puzzle_num} Solver")
        print("="*70)
        print(f"Range: 2^{self.config.range_min.bit_length()-1} to 2^{self.config.range_max.bit_length()-1}")
        print(f"Size: {self.range_size:,} keys")
        print(f"Prize: {self.config.prize_btc} BTC")
        print(f"Status: {self.config.status}")
        print(f"Workers: {self.workers} CPU cores")
        print(f"Starting from: {self.start_key:,}")
        print("="*70)
        print()

        # Divide work among workers
        keys_per_worker = self.range_size // self.workers
        processes = []

        for i in range(self.workers):
            worker_start = self.start_key + (i * keys_per_worker)
            worker_end = worker_start + keys_per_worker

            if i == self.workers - 1:
                # Last worker gets any remainder
                worker_end = self.config.range_max

            p = multiprocessing.Process(
                target=self._worker_process,
                args=(i, worker_start, worker_end),
                name=f"PuzzleWorker-{i}"
            )
            p.start()
            processes.append(p)

        print(f"Launched {self.workers} worker processes")
        print()

        # Monitor progress
        start_time = time.time()
        total_keys_checked = 0
        worker_progress = {i: self.start_key + (i * keys_per_worker) for i in range(self.workers)}
        last_checkpoint = time.time()
        checkpoint_interval = 60.0  # Save every minute

        while any(p.is_alive() for p in processes):
            try:
                # Check for result
                if not self.result_queue.empty():
                    result = self.result_queue.get()
                    if result.get('found'):
                        print("\n" + "="*70)
                        print("🎉 PRIVATE KEY FOUND!")
                        print("="*70)
                        print(f"Private Key (decimal): {result['private_key']}")
                        print(f"Private Key (hex): 0x{result['private_key']:x}")
                        print(f"Found by worker: {result['worker_id']}")
                        print("="*70)

                        # Stop all workers
                        self.stop_event.set()
                        for p in processes:
                            p.join(timeout=2)

                        return result['private_key']

                # Collect stats
                while not self.stats_queue.empty():
                    stat = self.stats_queue.get()
                    worker_id = stat['worker_id']
                    total_keys_checked += stat['keys_checked']
                    worker_progress[worker_id] = stat['current_key']

                # Display progress
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = total_keys_checked / elapsed
                    max_progress_key = max(worker_progress.values())
                    progress_pct = ((max_progress_key - self.config.range_min) / self.range_size * 100)

                    # Estimate time remaining
                    keys_remaining = self.config.range_max - max_progress_key
                    if rate > 0:
                        eta_seconds = keys_remaining / rate
                        # Handle astronomically large ETAs
                        if eta_seconds > 999999999999:  # > ~31k years
                            years = eta_seconds / (365.25 * 24 * 3600)
                            if years > 1_000_000_000:
                                eta = f"{years/1_000_000_000:.1f}B years"
                            elif years > 1_000_000:
                                eta = f"{years/1_000_000:.1f}M years"
                            else:
                                eta = f"{years:,.0f} years"
                        else:
                            eta = timedelta(seconds=int(eta_seconds))
                    else:
                        eta = "Unknown"

                    print(f"\r{' ' * 120}\r", end='')
                    print(
                        f"Progress: {progress_pct:.6f}% | "
                        f"Keys: {total_keys_checked:,} | "
                        f"Rate: {rate:,.0f} k/s | "
                        f"ETA: {eta} | "
                        f"Time: {timedelta(seconds=int(elapsed))}",
                        end='',
                        flush=True
                    )

                # Save checkpoint
                if time.time() - last_checkpoint >= checkpoint_interval:
                    max_progress_key = max(worker_progress.values())
                    self._save_checkpoint(max_progress_key, total_keys_checked, elapsed)
                    last_checkpoint = time.time()

                time.sleep(0.5)

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                self.stop_event.set()
                break

        # Wait for workers
        for p in processes:
            p.join(timeout=5)

        # Final checkpoint
        if worker_progress:
            max_progress_key = max(worker_progress.values())
            elapsed = time.time() - start_time
            self._save_checkpoint(max_progress_key, total_keys_checked, elapsed)

        print("\n\nSearch completed (no key found)")
        return None


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Bitcoin Puzzle Solver - CPU Optimized')
    parser.add_argument('puzzle_num', type=int, help='Puzzle number (10, 20, 30, 66, etc.)')
    parser.add_argument('-w', '--workers', type=int, help='Number of worker processes')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--checkpoint', type=str, help='Checkpoint file path')

    args = parser.parse_args()

    if args.puzzle_num not in PUZZLES:
        print(f"Puzzle #{args.puzzle_num} not found")
        print(f"Available puzzles: {list(PUZZLES.keys())}")
        return 1

    config = PUZZLES[args.puzzle_num]

    print(f"\nInitializing Puzzle #{args.puzzle_num} solver...")
    print(f"Prize: {config.prize_btc} BTC (~${config.prize_btc * 60000:,.0f} at $60k/BTC)")
    print()

    searcher = PuzzleSearcher(
        config=config,
        workers=args.workers,
        checkpoint_file=args.checkpoint
    )

    result = searcher.search()

    if result:
        print(f"\nSuccess! Save this key securely.")
        return 0
    else:
        print(f"\nSearch incomplete. Resume with --resume flag.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
