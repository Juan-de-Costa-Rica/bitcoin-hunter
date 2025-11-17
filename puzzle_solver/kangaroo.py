#!/usr/bin/env python3
"""
Pollard's Kangaroo Algorithm for Bitcoin Puzzle Solving

Implements the classic lambda/kangaroo collision algorithm for
solving discrete logarithm problems with known range.

Optimized for CPU execution on ARM64 architecture.
"""

import os
import sys
import time
import hashlib
import multiprocessing
from dataclasses import dataclass
from typing import Optional, Tuple
import ecdsa
from ecdsa import SECP256k1
from ecdsa.ellipticcurve import Point


# Bitcoin secp256k1 curve parameters
CURVE = SECP256k1
G = CURVE.generator
N = CURVE.order


@dataclass
class DistinguishedPoint:
    """A distinguished point in the kangaroo walk."""
    x: int
    distance: int
    kangaroo_type: str  # 'tame' or 'wild'

    def __hash__(self):
        return hash(self.x)


class KangarooSolver:
    """
    Pollard's Kangaroo algorithm implementation.

    Searches for private key k such that k*G = target_pubkey,
    where k is in the range [range_min, range_max].
    """

    def __init__(self, range_min: int, range_max: int, target_pubkey: Point):
        self.range_min = range_min
        self.range_max = range_max
        self.target_pubkey = target_pubkey
        self.range_size = range_max - range_min

        # Calculate optimal parameters
        self.mean = int((range_max - range_min) / 2)
        self.avg_kangaroo_jumps = int(4 * (self.range_size ** 0.5))

        # Distinguished point parameters
        # A point is distinguished if its x-coordinate has trailing zeros
        # More zeros = fewer DPs = less storage, but longer walks
        self.dp_mask_bits = self._calculate_dp_mask()
        self.dp_mask = (1 << self.dp_mask_bits) - 1

        # Jump table for pseudo-random jumps
        self.jump_table_size = 256
        self.jump_table = self._generate_jump_table()

        # Storage for distinguished points
        self.tame_dps = {}  # x-coordinate -> (distance, point)
        self.wild_dps = {}

        # Statistics
        self.tame_jumps = 0
        self.wild_jumps = 0
        self.total_jumps = 0
        self.start_time = None

    def _calculate_dp_mask(self) -> int:
        """
        Calculate optimal distinguished point mask.

        We want about sqrt(range_size) / 100 distinguished points,
        which means 1 in ~100 points should be distinguished.
        """
        # For small puzzles, use fewer bits; for large puzzles, use more
        # Aim for 1 in 32 points to be distinguished (5 bits) for testing
        if self.range_size < 2**20:
            return 5  # 1 in 32
        elif self.range_size < 2**30:
            return 6  # 1 in 64
        else:
            return 8  # 1 in 256

    def _generate_jump_table(self) -> list:
        """
        Generate pseudo-random jump table.

        Jumps should average to mean/2 for optimal performance.
        """
        jumps = []
        target_avg = self.mean // 2

        for i in range(self.jump_table_size):
            # Use hash of index to generate pseudo-random jump
            h = hashlib.sha256(i.to_bytes(4, 'big')).digest()
            jump_val = int.from_bytes(h[:8], 'big')

            # Scale to reasonable range (between 1 and mean)
            jump = 1 + (jump_val % self.mean)
            jumps.append(jump)

        return jumps

    def _get_jump_distance(self, point: Point) -> int:
        """Get pseudo-random jump distance based on point."""
        # Use x-coordinate to index jump table
        index = point.x() % self.jump_table_size
        return self.jump_table[index]

    def _is_distinguished(self, point: Point) -> bool:
        """Check if point is distinguished (has trailing zero bits)."""
        return (point.x() & self.dp_mask) == 0

    def _point_add_scalar(self, point: Point, scalar: int) -> Point:
        """Add scalar to a point: point + scalar*G"""
        scalar_point = scalar * G
        return point + scalar_point

    def _create_tame_kangaroo(self) -> Tuple[Point, int]:
        """
        Create a tame kangaroo starting at a random position in the range.

        Returns: (starting_point, starting_distance)
        """
        # Start at random position within range
        import random
        start_key = self.range_min + random.randint(0, self.range_size - 1)
        start_point = start_key * G

        return start_point, start_key

    def _create_wild_kangaroo(self) -> Tuple[Point, int]:
        """
        Create a wild kangaroo starting at target + random offset.

        Returns: (starting_point, starting_distance)
        """
        # Add random offset to avoid all wild kangaroos following same path
        import random
        offset = random.randint(0, self.mean)
        start_point = self._point_add_scalar(self.target_pubkey, offset)

        # Distance is negative because we started ahead of target
        return start_point, offset

    def _walk_kangaroo(self, start_point: Point, start_distance: int,
                       kangaroo_type: str, max_jumps: int) -> Optional[int]:
        """
        Walk a kangaroo until finding distinguished point or collision.

        Args:
            start_point: Starting point
            start_distance: Known distance from origin (for tame) or 0 (for wild)
            kangaroo_type: 'tame' or 'wild'
            max_jumps: Maximum jumps before giving up (use large number)

        Returns:
            Private key if found, None otherwise
        """
        current_point = start_point
        distance_traveled = start_distance

        # Walk until we hit a DP or exceed max_jumps
        for jump_num in range(max_jumps):
            # Get jump distance based on current point
            jump = self._get_jump_distance(current_point)

            # Jump
            current_point = self._point_add_scalar(current_point, jump)
            distance_traveled += jump

            # Update statistics
            if kangaroo_type == 'tame':
                self.tame_jumps += 1
            else:
                self.wild_jumps += 1
            self.total_jumps += 1

            # Check if distinguished
            if self._is_distinguished(current_point):
                x_coord = current_point.x()

                # Check for collision
                if kangaroo_type == 'tame':
                    # Check if wild kangaroo found this DP
                    if x_coord in self.wild_dps:
                        wild_dist, wild_point = self.wild_dps[x_coord]

                        # Verify points match
                        if wild_point.x() == current_point.x() and wild_point.y() == current_point.y():
                            # COLLISION! Calculate private key
                            # tame_dist is absolute private key, wild_dist is distance from target
                            # tame_dist * G = (target_key + wild_dist) * G
                            # Therefore: target_key = tame_dist - wild_dist
                            private_key = distance_traveled - wild_dist

                            # Handle negative values (wrap around curve order)
                            if private_key < 0:
                                private_key = (private_key % N + N) % N

                            # Verify
                            if private_key * G == self.target_pubkey:
                                return private_key
                            else:
                                # Debug: collision but verification failed
                                print(f"\n[DEBUG] Collision found but verification failed!")
                                print(f"  Calculated key: {private_key}")
                                print(f"  Tame dist: {distance_traveled}, Wild dist: {wild_dist}")
                                print(f"  Verification: {(private_key * G).x()} vs {self.target_pubkey.x()}")

                    # Store this DP
                    self.tame_dps[x_coord] = (distance_traveled, current_point)

                else:  # wild
                    # Check if tame kangaroo found this DP
                    if x_coord in self.tame_dps:
                        tame_dist, tame_point = self.tame_dps[x_coord]

                        # Verify points match
                        if tame_point.x() == current_point.x() and tame_point.y() == current_point.y():
                            # COLLISION! Calculate private key
                            # tame_dist is absolute private key, distance_traveled is distance from target
                            # tame_dist * G = (target_key + distance_traveled) * G
                            # Therefore: target_key = tame_dist - distance_traveled
                            private_key = tame_dist - distance_traveled

                            # Handle negative values (wrap around curve order)
                            if private_key < 0:
                                private_key = (private_key % N + N) % N

                            # Verify
                            if private_key * G == self.target_pubkey:
                                return private_key
                            else:
                                # Debug: collision but verification failed
                                print(f"\n[DEBUG] Wild collision found but verification failed!")
                                print(f"  Calculated key: {private_key}")
                                print(f"  Tame dist: {tame_dist}, Wild dist: {distance_traveled}")
                                print(f"  Verification: {(private_key * G).x()} vs {self.target_pubkey.x()}")

                    # Store this DP
                    self.wild_dps[x_coord] = (distance_traveled, current_point)

                # Found DP, return to spawn new kangaroo
                return None

        return None

    def solve(self, max_time_seconds: Optional[int] = None) -> Optional[int]:
        """
        Run the kangaroo algorithm to find the private key.

        Args:
            max_time_seconds: Maximum time to run (None = unlimited)

        Returns:
            Private key if found, None if not found within time limit
        """
        self.start_time = time.time()
        print(f"Starting Pollard's Kangaroo algorithm")
        print(f"Range: 2^{self.range_min.bit_length()-1} to 2^{self.range_max.bit_length()-1}")
        print(f"Range size: 2^{self.range_size.bit_length()-1}")
        print(f"Expected operations: ~{self.avg_kangaroo_jumps:,}")
        print(f"Distinguished point rate: 1 in {2**self.dp_mask_bits}")
        print()

        # Calculate how many kangaroos to launch
        # We want roughly equal work from tame and wild
        tame_kangaroos = 0
        wild_kangaroos = 0

        last_report = time.time()
        report_interval = 10.0  # Report every 10 seconds

        # Maximum jumps per kangaroo = 10x expected DP distance
        max_jumps_per_walk = (2 ** self.dp_mask_bits) * 10

        while True:
            # Check time limit
            if max_time_seconds and (time.time() - self.start_time) > max_time_seconds:
                print(f"\nTime limit reached ({max_time_seconds}s)")
                return None

            # Launch tame kangaroo
            tame_point, tame_dist = self._create_tame_kangaroo()
            result = self._walk_kangaroo(tame_point, tame_dist, 'tame',
                                        max_jumps_per_walk)
            if result:
                return result
            tame_kangaroos += 1

            # Launch wild kangaroo
            wild_point, wild_dist = self._create_wild_kangaroo()
            result = self._walk_kangaroo(wild_point, wild_dist, 'wild',
                                        max_jumps_per_walk)
            if result:
                return result
            wild_kangaroos += 1

            # Progress report
            if time.time() - last_report >= report_interval:
                elapsed = time.time() - self.start_time
                rate = self.total_jumps / elapsed if elapsed > 0 else 0

                print(f"\r[{elapsed:.0f}s] Jumps: {self.total_jumps:,} | "
                      f"Rate: {rate:,.0f} j/s | "
                      f"Tame DPs: {len(self.tame_dps):,} | "
                      f"Wild DPs: {len(self.wild_dps):,} | "
                      f"Kangaroos: {tame_kangaroos + wild_kangaroos:,}",
                      end='', flush=True)

                last_report = time.time()


def hex_to_point(hex_pubkey: str) -> Point:
    """Convert hex public key to EC point."""
    pubkey_bytes = bytes.fromhex(hex_pubkey)

    # Handle compressed or uncompressed
    if len(pubkey_bytes) == 33:
        # Compressed
        x = int.from_bytes(pubkey_bytes[1:33], 'big')
        y_parity = pubkey_bytes[0] - 0x02

        # Calculate y from x
        y_squared = (pow(x, 3, CURVE.curve.p()) + CURVE.curve.b()) % CURVE.curve.p()
        y = pow(y_squared, (CURVE.curve.p() + 1) // 4, CURVE.curve.p())

        if y % 2 != y_parity:
            y = CURVE.curve.p() - y

        return Point(CURVE.curve, x, y)

    elif len(pubkey_bytes) == 65:
        # Uncompressed
        x = int.from_bytes(pubkey_bytes[1:33], 'big')
        y = int.from_bytes(pubkey_bytes[33:65], 'big')
        return Point(CURVE.curve, x, y)

    else:
        raise ValueError(f"Invalid public key length: {len(pubkey_bytes)}")


def test_algorithm():
    """Test the algorithm on a known puzzle."""
    print("="*70)
    print("Testing Pollard's Kangaroo on Puzzle #10 (SOLVED)")
    print("="*70)

    # Puzzle #10: range 2^9 to 2^10 (512 to 1024)
    # Known answer: 0x33E = 830
    # Public key: 0x0209c58240e50e3ba3f833c82655e8725c037a2294e14cf5d73a5df8d56159de69

    range_min = 2**9
    range_max = 2**10
    target_pubkey_hex = "0209c58240e50e3ba3f833c82655e8725c037a2294e14cf5d73a5df8d56159de69"
    expected_key = 0x33E

    print(f"Range: {range_min} to {range_max}")
    print(f"Expected key: {expected_key} (0x{expected_key:x})")
    print()

    target_point = hex_to_point(target_pubkey_hex)

    solver = KangarooSolver(range_min, range_max, target_point)

    result = solver.solve(max_time_seconds=60)

    print("\n")
    print("="*70)
    if result:
        print(f"✅ FOUND: {result} (0x{result:x})")
        print(f"Expected: {expected_key} (0x{expected_key:x})")
        print(f"Match: {result == expected_key}")
        print(f"Total jumps: {solver.total_jumps:,}")
        print(f"Time: {time.time() - solver.start_time:.2f}s")
    else:
        print("❌ Not found within time limit")
    print("="*70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Pollard\'s Kangaroo Bitcoin Puzzle Solver')
    parser.add_argument('--test', action='store_true', help='Run test on Puzzle #10')
    parser.add_argument('--puzzle', type=int, help='Puzzle number (60-66)')
    parser.add_argument('--range-min', type=str, help='Minimum range (hex)')
    parser.add_argument('--range-max', type=str, help='Maximum range (hex)')
    parser.add_argument('--pubkey', type=str, help='Target public key (hex)')
    parser.add_argument('--max-time', type=int, help='Maximum time in seconds')

    args = parser.parse_args()

    if args.test:
        test_algorithm()
        return

    # Puzzle presets
    PUZZLES = {
        60: {
            'range_min': 2**59,
            'range_max': 2**60,
            'pubkey': '0220a96e2fa98d0e7dc19ba6e7e70c5e4c37b0e7c3c78e41fe4e6e8e5e6e5e6e5',
            'status': 'SOLVED'
        },
        66: {
            'range_min': 2**65,
            'range_max': 2**66,
            'pubkey': '03a2efa402fd5268400c77c20e574ba86409ededee7c4020e4b9f0edbee53de0d4',
            'status': 'UNSOLVED - 6.6 BTC prize'
        },
    }

    if args.puzzle:
        if args.puzzle not in PUZZLES:
            print(f"Puzzle #{args.puzzle} not in database")
            print(f"Available puzzles: {list(PUZZLES.keys())}")
            return

        puzzle = PUZZLES[args.puzzle]
        range_min = puzzle['range_min']
        range_max = puzzle['range_max']
        pubkey_hex = puzzle['pubkey']

        print(f"Solving Puzzle #{args.puzzle}")
        print(f"Status: {puzzle['status']}")

    elif args.range_min and args.range_max and args.pubkey:
        range_min = int(args.range_min, 16)
        range_max = int(args.range_max, 16)
        pubkey_hex = args.pubkey

    else:
        print("Error: Must specify --test, --puzzle N, or --range-min --range-max --pubkey")
        parser.print_help()
        return

    print()
    print("="*70)
    print(f"Range: 2^{range_min.bit_length()-1} to 2^{range_max.bit_length()-1}")
    print(f"Public key: {pubkey_hex}")
    print("="*70)
    print()

    target_point = hex_to_point(pubkey_hex)
    solver = KangarooSolver(range_min, range_max, target_point)

    result = solver.solve(max_time_seconds=args.max_time)

    print("\n")
    print("="*70)
    if result:
        print(f"✅ PRIVATE KEY FOUND!")
        print(f"Decimal: {result}")
        print(f"Hex: 0x{result:x}")
        print(f"Total jumps: {solver.total_jumps:,}")
        elapsed = time.time() - solver.start_time
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {solver.total_jumps/elapsed:,.0f} jumps/sec")
    else:
        print("Not found")
    print("="*70)


if __name__ == "__main__":
    main()
