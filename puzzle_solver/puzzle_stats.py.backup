#!/usr/bin/env python3
"""
Bitcoin Puzzle Solver - Statistics Viewer

View progress, performance, and system resources for puzzle solving.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta


def load_checkpoint(puzzle_num):
    """Load checkpoint data for a puzzle."""
    checkpoint_file = f"puzzle_{puzzle_num}_checkpoint.json"

    if not os.path.exists(checkpoint_file):
        return None

    try:
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    except:
        return None


def get_puzzle_config(puzzle_num):
    """Get puzzle configuration."""
    puzzles = {
        71: {
            'range_min': 2**70,
            'range_max': 2**71,
            'prize_btc': 7.1,
            'status': 'UNSOLVED - $426k'
        }
    }
    return puzzles.get(puzzle_num)


def get_process_info():
    """Get resource usage for puzzle_search process."""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.split('\n'):
            if 'puzzle_search.py' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    return {
                        'pid': parts[1],
                        'cpu': parts[2],
                        'mem': parts[3],
                        'running': True
                    }

        return {'running': False}
    except:
        return {'running': False}


def get_system_resources():
    """Get overall system resource usage."""
    resources = {}

    try:
        # Load averages
        with open('/proc/loadavg', 'r') as f:
            loads = f.read().split()[:3]
            resources['load_1min'] = float(loads[0])
            resources['load_5min'] = float(loads[1])
            resources['load_15min'] = float(loads[2])
    except:
        pass

    try:
        # Memory info
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    meminfo[key] = int(value)

            total_mem = meminfo.get('MemTotal', 0)
            avail_mem = meminfo.get('MemAvailable', 0)
            used_mem = total_mem - avail_mem

            resources['mem_total_gb'] = total_mem / 1024 / 1024
            resources['mem_used_gb'] = used_mem / 1024 / 1024
            resources['mem_used_pct'] = (used_mem / total_mem * 100) if total_mem > 0 else 0
    except:
        pass

    try:
        # CPU count
        result = subprocess.run(['nproc'], capture_output=True, text=True, timeout=2)
        resources['cpu_count'] = int(result.stdout.strip())
    except:
        pass

    return resources


def format_large_number(n):
    """Format very large numbers readably."""
    if n < 1000:
        return str(n)
    elif n < 1_000_000:
        return f"{n/1000:.2f}K"
    elif n < 1_000_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n < 1_000_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    elif n < 1_000_000_000_000_000:
        return f"{n/1_000_000_000_000:.2f}T"
    elif n < 1_000_000_000_000_000_000:
        return f"{n/1_000_000_000_000_000:.2f}Q"
    else:
        return f"{n/1_000_000_000_000_000_000:.2f}Qi"


def display_stats(puzzle_num):
    """Display comprehensive puzzle solving statistics."""
    print("="*70)
    print(f"Bitcoin Puzzle #{puzzle_num} Solver - Statistics")
    print("="*70)
    print()

    # Load checkpoint
    checkpoint = load_checkpoint(puzzle_num)
    config = get_puzzle_config(puzzle_num)

    if not config:
        print(f"❌ Puzzle #{puzzle_num} not configured")
        return

    if not checkpoint:
        print("⚠️  No checkpoint data available")
        print(f"\nPuzzle #{puzzle_num} solver hasn't been started yet.")
        print(f"Start with: python3 puzzle_search.py {puzzle_num} -w 3")
        return

    # Calculate progress
    range_min = config['range_min']
    range_max = config['range_max']
    range_size = range_max - range_min

    last_key = checkpoint.get('last_key_checked', range_min)
    keys_checked = checkpoint.get('keys_checked', 0)
    elapsed = checkpoint.get('elapsed_seconds', 0)
    timestamp = checkpoint.get('timestamp', 'Unknown')

    # Calculate ACTUAL progress based on keys checked, not worker position
    actual_progress_pct = (keys_checked / range_size * 100) if range_size > 0 else 0

    print("📊 PUZZLE PROGRESS")
    print("-"*70)
    print(f"Puzzle Number:               #{puzzle_num}")
    print(f"Prize:                       {config['prize_btc']} BTC (${config['prize_btc'] * 60000:,.0f} @ $60k)")
    print(f"Status:                      {config['status']}")
    print()
    print(f"Range Start:                 {format_large_number(range_min)} (2^70)")
    print(f"Range End:                   {format_large_number(range_max)} (2^71)")
    print(f"Range Size:                  {format_large_number(range_size)} keys")
    print()
    print(f"Keys Checked:                {keys_checked:,}")
    print(f"Actual Progress:             {actual_progress_pct:.20f}%")
    print()

    # Time statistics
    if elapsed > 0:
        rate = keys_checked / elapsed
        print(f"Elapsed Time:                {timedelta(seconds=int(elapsed))}")
        print(f"Average Rate:                {rate:,.0f} keys/sec")
        print()

        # ETA calculation
        keys_remaining = range_max - last_key
        if rate > 0:
            eta_seconds = keys_remaining / rate
            years = eta_seconds / (365.25 * 24 * 3600)

            print("⏱️  TIME ESTIMATES")
            print("-"*70)
            if years > 1_000_000_000:
                print(f"Estimated Time Remaining:    {years/1_000_000_000:.1f} billion years")
            elif years > 1_000_000:
                print(f"Estimated Time Remaining:    {years/1_000_000:.1f} million years")
            elif years > 1000:
                print(f"Estimated Time Remaining:    {years/1000:.1f} thousand years")
            elif years > 1:
                print(f"Estimated Time Remaining:    {years:.1f} years")
            else:
                # Only create timedelta for reasonable durations
                if eta_seconds < 999999999999:
                    eta = timedelta(seconds=int(eta_seconds))
                    print(f"Estimated Time Remaining:    {eta}")
                else:
                    print(f"Estimated Time Remaining:    {years:.1f} years")
            print()

    # Last checkpoint time
    print("💾 CHECKPOINT INFO")
    print("-"*70)
    print(f"Last Checkpoint:             {timestamp}")
    if os.path.exists(f"puzzle_{puzzle_num}_checkpoint.json"):
        checkpoint_size = os.path.getsize(f"puzzle_{puzzle_num}_checkpoint.json")
        print(f"Checkpoint File Size:        {checkpoint_size} bytes")
    print()

    # System resources
    print("💻 SYSTEM RESOURCES")
    print("-"*70)

    proc_info = get_process_info()
    sys_res = get_system_resources()

    if proc_info.get('running'):
        print(f"Solver Status:               ✅ RUNNING (PID {proc_info['pid']})")
        print(f"Solver CPU Usage:            {proc_info['cpu']}%")
        print(f"Solver Memory:               {proc_info['mem']}%")
    else:
        print(f"Solver Status:               ⏸️  NOT RUNNING")
        print()
        print("💡 Start the solver with:")
        print(f"   python3 puzzle_search.py {puzzle_num} -w 3 --resume")

    if 'cpu_count' in sys_res:
        print(f"CPU Cores:                   {sys_res['cpu_count']}")

    if 'load_1min' in sys_res:
        load_pct = (sys_res['load_1min'] / sys_res.get('cpu_count', 1)) * 100
        print(f"System Load (1/5/15min):     {sys_res['load_1min']:.2f} / {sys_res['load_5min']:.2f} / {sys_res['load_15min']:.2f}")
        if 'cpu_count' in sys_res:
            print(f"Load Percentage:             {load_pct:.1f}% (of {sys_res['cpu_count']} cores)")

    if 'mem_total_gb' in sys_res:
        print(f"Memory Used:                 {sys_res['mem_used_gb']:.1f} GB / {sys_res['mem_total_gb']:.1f} GB ({sys_res['mem_used_pct']:.1f}%)")

    print()
    print("="*70)
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()
    print("💡 This is an educational project demonstrating Bitcoin's cryptographic")
    print("   security. The probability of finding the key is astronomically low.")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Puzzle solver statistics viewer')
    parser.add_argument('puzzle_num', type=int, nargs='?', default=71, help='Puzzle number (default: 71)')
    args = parser.parse_args()

    try:
        display_stats(args.puzzle_num)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
