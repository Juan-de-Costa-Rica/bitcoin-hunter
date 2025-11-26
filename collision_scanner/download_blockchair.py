#!/usr/bin/env python3
"""
Download Bitcoin address database from Blockchair.

Downloads the latest dump of all Bitcoin addresses with balances from Blockchair.
Free, updated daily, includes ~50-60 million addresses.
"""

import os
import sys
import requests
import gzip
import time
from datetime import datetime


# Configuration
BLOCKCHAIR_URL = "https://gz.blockchair.com/bitcoin/addresses/blockchair_bitcoin_addresses_latest.tsv.gz"
DATA_DIR = "data"
COMPRESSED_FILE = os.path.join(DATA_DIR, "blockchair_addresses.tsv.gz")
OUTPUT_FILE = os.path.join(DATA_DIR, "addresses.txt")


def download_file(url, output_path):
    """Download file with progress bar."""
    print(f"Downloading from: {url}")
    print(f"Saving to: {output_path}\n")

    try:
        # Start download with streaming
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))

        if total_size == 0:
            print("Note: File size unknown, progress percentage not available")
        else:
            print(f"File size: {total_size / (1024**3):.2f} GB")

        # Download with progress
        downloaded = 0
        start_time = time.time()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Progress update every 10 MB
                    if downloaded % (10 * 1024 * 1024) == 0 or downloaded == total_size:
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            eta = (total_size - downloaded) / speed if speed > 0 else 0
                            print(f"  {downloaded / (1024**2):.1f} MB / {total_size / (1024**2):.1f} MB "
                                  f"({percent:.1f}%) - {speed / 1024:.1f} KB/s - ETA: {eta:.0f}s",
                                  end='\r')
                        else:
                            print(f"  Downloaded: {downloaded / (1024**2):.1f} MB - "
                                  f"{speed / 1024:.1f} KB/s",
                                  end='\r')

        elapsed = time.time() - start_time
        print(f"\n\n✓ Download complete!")
        print(f"  Total: {downloaded / (1024**2):.1f} MB")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"  Avg speed: {downloaded / elapsed / 1024:.1f} KB/s")

        return True

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Download failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n\n✗ Download cancelled by user")
        return False


def extract_addresses(compressed_file, output_file):
    """Extract addresses from compressed TSV file."""
    print(f"\nExtracting addresses from {compressed_file}...")
    print("This may take a while...\n")

    try:
        address_count = 0
        start_time = time.time()

        with gzip.open(compressed_file, 'rt', encoding='utf-8') as f_in:
            with open(output_file, 'w') as f_out:
                # Skip header line
                header = f_in.readline()
                print(f"Columns: {header.strip()}")
                print()

                # Process each line
                for line in f_in:
                    parts = line.strip().split('\t')

                    # First column should be the address
                    if parts and len(parts[0]) > 0:
                        address = parts[0]

                        # Basic validation (Bitcoin addresses are 26-35 characters)
                        if 26 <= len(address) <= 62:  # Bech32 can be longer
                            f_out.write(f"{address}\n")
                            address_count += 1

                            # Progress update
                            if address_count % 100000 == 0:
                                elapsed = time.time() - start_time
                                rate = address_count / elapsed if elapsed > 0 else 0
                                print(f"  Extracted: {address_count:,} addresses ({rate:,.0f}/sec)",
                                      end='\r')

        elapsed = time.time() - start_time
        print(f"\n\n✓ Extraction complete!")
        print(f"  Total addresses: {address_count:,}")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"  Output: {output_file}")

        # Get file size
        file_size = os.path.getsize(output_file)
        print(f"  Size: {file_size / (1024**2):.1f} MB")

        return True

    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        return False


def main():
    """Main entry point."""
    print("="*70)
    print("Blockchair Bitcoin Address Database Downloader")
    print("="*70)
    print()
    print("This will download the latest database of all Bitcoin addresses")
    print("with balances from Blockchair (~50-60 million addresses).")
    print()
    print("File details:")
    print("  - Source: Blockchair (https://blockchair.com/dumps)")
    print("  - Format: TSV compressed with gzip")
    print("  - Size: ~1.5-3 GB compressed, ~4-8 GB uncompressed")
    print("  - Updated: Daily")
    print("  - License: CC BY 4.0 (Free)")
    print()
    print("⚠️  NOTE: Download speed is limited to 10 KB/s by Blockchair")
    print("   This may take 1-2 hours to complete.")
    print()

    # Confirm
    response = input("Continue with download? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Create data directory
    os.makedirs(DATA_DIR, exist_ok=True)

    # Download compressed file
    print("\n" + "="*70)
    print("STEP 1: Downloading compressed file")
    print("="*70)

    if not download_file(BLOCKCHAIR_URL, COMPRESSED_FILE):
        print("\nDownload failed. Exiting.")
        return

    # Extract addresses
    print("\n" + "="*70)
    print("STEP 2: Extracting addresses")
    print("="*70)

    if not extract_addresses(COMPRESSED_FILE, OUTPUT_FILE):
        print("\nExtraction failed. Exiting.")
        return

    # Cleanup
    print("\n" + "="*70)
    print("STEP 3: Cleanup")
    print("="*70)

    response = input(f"\nDelete compressed file ({COMPRESSED_FILE}) to save space? (y/n): ")
    if response.lower() == 'y':
        os.remove(COMPRESSED_FILE)
        print(f"✓ Deleted {COMPRESSED_FILE}")

    # Summary
    print("\n" + "="*70)
    print("COMPLETE!")
    print("="*70)
    print(f"\n✓ Address database ready: {OUTPUT_FILE}")
    print("\nNext step: python3 import_db.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
