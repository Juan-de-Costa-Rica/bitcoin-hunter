#!/usr/bin/env python3
"""
Download Bitcoin address database from various sources.

This script fetches a list of Bitcoin addresses that have ever had a balance.
Multiple sources are supported as fallbacks.
"""

import os
import sys
import requests
import gzip
import json
from datetime import datetime


DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "addresses.txt")


def download_from_blockchair():
    """
    Download from Blockchair's database dumps.
    Note: Blockchair offers paid API access and database dumps.
    """
    print("Blockchair requires an API key for bulk downloads.")
    print("Visit: https://blockchair.com/api/docs#link_M03")
    return False


def download_from_github_sample():
    """
    Download a sample address list from GitHub for testing.
    This is NOT a complete database, just for testing purposes.
    """
    print("\n[GitHub Sample] Downloading sample address list...")

    # Sample known addresses for testing (these are public addresses from blockchain explorers)
    sample_addresses = [
        # Genesis block reward (Satoshi's address)
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        # Early Bitcoin addresses
        "12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX",
        "1HLoD9E4SDFFPDiYfNYnkBLQ85Y51J3Zb1",
        # BitPay addresses
        "3E8ociqZa9mZUSwGdSmAEMAoAxBK3FNDcd",
        # Binance cold wallet
        "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
        # Add more for testing...
    ]

    try:
        with open(OUTPUT_FILE, 'w') as f:
            for addr in sample_addresses:
                f.write(f"{addr}\n")

        print(f"✓ Downloaded {len(sample_addresses)} sample addresses to {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def build_from_api():
    """
    Build address database by querying blockchain APIs.
    This is SLOW but works without downloading large files.

    We'll query recent blocks and extract addresses from transactions.
    """
    print("\n[API Method] Building address database from blockchain APIs...")
    print("This may take a very long time for comprehensive coverage.")
    print("Recommended: Use pre-built database instead.")

    response = input("\nContinue with API method? (y/n): ")
    if response.lower() != 'y':
        return False

    addresses = set()

    try:
        # Get latest block height
        print("Fetching latest block info...")
        r = requests.get("https://blockchain.info/latestblock", timeout=10)
        latest_height = r.json()['height']

        print(f"Latest block: {latest_height}")
        print("Fetching addresses from recent blocks...")

        # Fetch addresses from recent blocks (last 100 blocks as sample)
        for height in range(latest_height - 100, latest_height + 1):
            print(f"Processing block {height}...", end='\r')

            try:
                # Get block hash
                r = requests.get(f"https://blockchain.info/block-height/{height}?format=json", timeout=10)
                block_data = r.json()

                # Extract addresses from transactions
                for block in block_data.get('blocks', []):
                    for tx in block.get('tx', []):
                        # Output addresses
                        for out in tx.get('out', []):
                            if 'addr' in out:
                                addresses.add(out['addr'])

                        # Input addresses (from previous outputs)
                        for inp in tx.get('inputs', []):
                            if 'prev_out' in inp and 'addr' in inp['prev_out']:
                                addresses.add(inp['prev_out']['addr'])

            except Exception as e:
                print(f"\nError processing block {height}: {e}")
                continue

        print(f"\n\nCollected {len(addresses)} unique addresses")

        # Save to file
        with open(OUTPUT_FILE, 'w') as f:
            for addr in sorted(addresses):
                f.write(f"{addr}\n")

        print(f"✓ Saved to {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def download_manual_instructions():
    """
    Provide instructions for manually downloading address databases.
    """
    print("\n" + "="*70)
    print("MANUAL DOWNLOAD INSTRUCTIONS")
    print("="*70)
    print("""
Since automated downloads from comprehensive sources require API keys
or subscriptions, here are manual options:

1. **Blockchair Database Dumps** (Recommended)
   - Visit: https://gz.blockchair.com/bitcoin/addresses/
   - Download: Latest addresses dump (several GB)
   - Extract to: data/addresses.txt
   - Format: One address per line

2. **Bitcoin Rich List**
   - Visit: https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html
   - Download: Address lists (smaller, top addresses only)

3. **GitHub Datasets**
   - Search: "bitcoin addresses dataset" on GitHub
   - Many researchers publish address lists

4. **Build Your Own** (Advanced)
   - Run Bitcoin Core full node
   - Use `listunspent` RPC command
   - Export all addresses with balances

After downloading, place the file at:
    {output}

Format should be: one address per line (plain text)
Example:
    1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
    12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX
    ...

Then run: python3 import_db.py
""".format(output=OUTPUT_FILE))
    print("="*70)


def main():
    """Main entry point."""
    print("="*70)
    print("Bitcoin Address Database Downloader")
    print("="*70)

    # Create data directory
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\nAvailable methods:")
    print("  1. Download sample addresses (for testing)")
    print("  2. Build from API (slow, limited coverage)")
    print("  3. Manual download instructions")
    print()

    choice = input("Select method (1/2/3): ").strip()

    if choice == "1":
        success = download_from_github_sample()
    elif choice == "2":
        success = build_from_api()
    elif choice == "3":
        download_manual_instructions()
        return
    else:
        print("Invalid choice")
        return

    if success:
        print("\n✓ Address database download complete!")
        print(f"  Location: {OUTPUT_FILE}")
        print(f"\nNext step: python3 import_db.py")
    else:
        print("\n✗ Download failed")
        print("\nFalling back to manual instructions...")
        download_manual_instructions()


if __name__ == "__main__":
    main()
