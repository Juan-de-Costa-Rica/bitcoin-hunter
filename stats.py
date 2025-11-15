#!/usr/bin/env python3
"""
Bitcoin Address Hunter - Statistics Viewer

View cumulative statistics from running or completed scans.
Parse logs to show total progress over time.
"""

import os
import sys
import re
from datetime import datetime, timedelta
from collections import defaultdict


# Configuration
STATS_LOG = "logs/stats.log"
FOUND_LOG = "logs/found.txt"
ERROR_LOG = "logs/errors.log"


def parse_stats_log():
    """Parse stats.log to get cumulative statistics."""
    if not os.path.exists(STATS_LOG):
        return None

    stats_entries = []

    with open(STATS_LOG, 'r') as f:
        for line in f:
            # Format: 2025-11-15 02:44:35,336 - Stats: 765 keys, 2,295 addrs, 765 k/s avg, 0 found, 0 errors
            match = re.search(
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Stats: ([\d,]+) keys, ([\d,]+) addrs, ([\d.]+) k/s avg, (\d+) found, (\d+) errors',
                line
            )
            if match:
                timestamp_str = match.group(1)
                keys = int(match.group(2).replace(',', ''))
                addresses = int(match.group(3).replace(',', ''))
                rate = float(match.group(4))
                found = int(match.group(5))
                errors = int(match.group(6))

                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    continue

                stats_entries.append({
                    'timestamp': timestamp,
                    'keys': keys,
                    'addresses': addresses,
                    'rate': rate,
                    'found': found,
                    'errors': errors
                })

    return stats_entries


def get_latest_stats():
    """Get the most recent statistics."""
    stats_entries = parse_stats_log()

    if not stats_entries:
        return None

    return stats_entries[-1]


def get_total_runtime(stats_entries):
    """Calculate total runtime from first to last log entry."""
    if not stats_entries or len(stats_entries) < 2:
        return None

    first = stats_entries[0]['timestamp']
    last = stats_entries[-1]['timestamp']

    return last - first


def count_found():
    """Count found addresses from found.txt."""
    if not os.path.exists(FOUND_LOG):
        return 0

    count = 0
    with open(FOUND_LOG, 'r') as f:
        for line in f:
            if line.startswith("FOUND AT:"):
                count += 1

    return count


def count_errors():
    """Count total errors from error log."""
    if not os.path.exists(ERROR_LOG):
        return 0

    count = 0
    with open(ERROR_LOG, 'r') as f:
        for line in f:
            if " - ERROR - " in line:
                count += 1

    return count


def get_error_summary():
    """Get summary of error types."""
    if not os.path.exists(ERROR_LOG):
        return {}

    error_types = defaultdict(int)

    with open(ERROR_LOG, 'r') as f:
        for line in f:
            if " - ERROR - " in line:
                # Try to extract error type
                if "Database" in line:
                    error_types["Database errors"] += 1
                elif "generation failed" in line:
                    error_types["Key generation errors"] += 1
                elif "Address generation failed" in line:
                    error_types["Address generation errors"] += 1
                elif "query error" in line:
                    error_types["Database query errors"] += 1
                else:
                    error_types["Other errors"] += 1

    return dict(error_types)


def get_hourly_progress(stats_entries):
    """Calculate progress by hour."""
    if not stats_entries:
        return []

    hourly = {}

    for entry in stats_entries:
        hour_key = entry['timestamp'].strftime('%Y-%m-%d %H:00')

        if hour_key not in hourly:
            hourly[hour_key] = {
                'keys': entry['keys'],
                'addresses': entry['addresses'],
                'avg_rate': [entry['rate']],
            }
        else:
            # Take max keys for this hour (cumulative)
            hourly[hour_key]['keys'] = max(hourly[hour_key]['keys'], entry['keys'])
            hourly[hour_key]['addresses'] = max(hourly[hour_key]['addresses'], entry['addresses'])
            hourly[hour_key]['avg_rate'].append(entry['rate'])

    # Calculate average rates
    for hour_key in hourly:
        rates = hourly[hour_key]['avg_rate']
        hourly[hour_key]['avg_rate'] = sum(rates) / len(rates)

    return sorted(hourly.items())


def display_stats():
    """Display comprehensive statistics."""
    print("="*70)
    print("Bitcoin Address Hunter - Statistics")
    print("="*70)
    print()

    # Parse stats log
    stats_entries = parse_stats_log()

    if not stats_entries:
        print("⚠️  No statistics available yet")
        print("\nScanner hasn't been running or logs directory doesn't exist.")
        print("Start the scanner with: python3 scanner_daemon.py")
        return

    # Latest stats
    latest = stats_entries[-1]

    print("📊 CURRENT STATISTICS")
    print("-"*70)
    print(f"Total Keys Generated:        {latest['keys']:,}")
    print(f"Total Addresses Checked:     {latest['addresses']:,}")
    print(f"Current Rate:                {latest['rate']:,.0f} keys/second")
    print(f"Addresses Found:             {latest['found']}")
    print(f"Errors Encountered:          {latest['errors']}")
    print()

    # Runtime calculation
    runtime = get_total_runtime(stats_entries)
    if runtime:
        print(f"Total Runtime:               {runtime}")
        print(f"First Log Entry:             {stats_entries[0]['timestamp']}")
        print(f"Last Log Entry:              {latest['timestamp']}")
        print()

    # Calculate some interesting stats
    total_seconds = runtime.total_seconds() if runtime else 0
    if total_seconds > 0:
        avg_rate = latest['keys'] / total_seconds
        print(f"Average Rate (overall):      {avg_rate:,.0f} keys/second")

        # Estimated addresses per day/week/month
        per_day = avg_rate * 86400
        per_week = per_day * 7
        per_month = per_day * 30

        print()
        print("📈 PROJECTIONS")
        print("-"*70)
        print(f"Estimated per day:           {per_day:,.0f} keys ({per_day*3:,.0f} addresses)")
        print(f"Estimated per week:          {per_week:,.0f} keys ({per_week*3:,.0f} addresses)")
        print(f"Estimated per month:         {per_month:,.0f} keys ({per_month*3:,.0f} addresses)")
        print()

    # Found addresses
    found_count = count_found()
    if found_count > 0:
        print("🎉 FOUND ADDRESSES")
        print("-"*70)
        print(f"Total Found:                 {found_count}")
        print(f"Details in:                  {FOUND_LOG}")
        print()
    else:
        print("🎯 LOTTERY STATUS")
        print("-"*70)
        print("No funded addresses found yet (as expected)")
        print(f"Probability: ~1 in 10^47 per address check")
        print()

    # Error summary
    error_count = count_errors()
    if error_count > 0:
        print("⚠️  ERROR SUMMARY")
        print("-"*70)
        print(f"Total Errors:                {error_count}")

        error_types = get_error_summary()
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error_type:30s} {count:,}")
        print()

    # Hourly progress (if more than 1 hour of data)
    if runtime and runtime.total_seconds() > 3600:
        print("⏰ HOURLY PROGRESS (Last 24 hours)")
        print("-"*70)

        hourly = get_hourly_progress(stats_entries)

        # Only show last 24 hours
        now = datetime.now()
        last_24h = [h for h in hourly if (now - datetime.strptime(h[0], '%Y-%m-%d %H:00')).total_seconds() <= 86400]

        if last_24h:
            for hour, data in last_24h[-24:]:
                print(f"{hour}  {data['keys']:>12,} keys  {data['avg_rate']:>6,.0f} k/s avg")
            print()

    # Database info
    db_file = "data/addresses.db"
    if os.path.exists(db_file):
        db_size = os.path.getsize(db_file) / (1024**2)  # MB
        print("💾 DATABASE INFO")
        print("-"*70)
        print(f"Database file:               {db_file}")
        print(f"Database size:               {db_size:.2f} MB")
        print()

    # File sizes
    print("📁 LOG FILES")
    print("-"*70)
    if os.path.exists(STATS_LOG):
        stats_size = os.path.getsize(STATS_LOG) / 1024  # KB
        print(f"Stats log:                   {stats_size:.2f} KB")
    if os.path.exists(ERROR_LOG):
        error_size = os.path.getsize(ERROR_LOG) / 1024  # KB
        print(f"Error log:                   {error_size:.2f} KB")
    if os.path.exists(FOUND_LOG):
        found_size = os.path.getsize(FOUND_LOG) / 1024  # KB
        print(f"Found log:                   {found_size:.2f} KB")

    print()
    print("="*70)
    print("Last updated:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*70)


def main():
    """Main entry point."""
    try:
        display_stats()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
