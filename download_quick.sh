#!/bin/bash
# Quick download of Blockchair Bitcoin address database
# This uses wget for resumable downloads

set -e

URL="https://gz.blockchair.com/bitcoin/addresses/blockchair_bitcoin_addresses_latest.tsv.gz"
DATA_DIR="data"
COMPRESSED_FILE="$DATA_DIR/blockchair_addresses.tsv.gz"
OUTPUT_FILE="$DATA_DIR/addresses.txt"

echo "======================================================================="
echo "Quick Blockchair Bitcoin Address Database Download"
echo "======================================================================="
echo
echo "Downloading: $URL"
echo "To: $COMPRESSED_FILE"
echo
echo "This may take 1-2 hours (10 KB/s speed limit from Blockchair)"
echo "You can safely Ctrl+C and resume later with the same command."
echo
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Create data directory
mkdir -p "$DATA_DIR"

# Download with wget (resumable)
echo
echo "======================================================================="
echo "STEP 1: Downloading (resumable)"
echo "======================================================================="
wget -c -O "$COMPRESSED_FILE" "$URL"

# Extract addresses (first column)
echo
echo "======================================================================="
echo "STEP 2: Extracting addresses"
echo "======================================================================="
echo "Extracting first column (addresses) from TSV file..."

zcat "$COMPRESSED_FILE" | tail -n +2 | cut -f1 > "$OUTPUT_FILE"

# Stats
ADDRESS_COUNT=$(wc -l < "$OUTPUT_FILE")
FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo
echo "✓ Extraction complete!"
echo "  Total addresses: $(printf "%'d" $ADDRESS_COUNT)"
echo "  File size: $FILE_SIZE"
echo "  Location: $OUTPUT_FILE"

# Offer to delete compressed file
echo
echo "======================================================================="
echo "Cleanup"
echo "======================================================================="
COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo "Compressed file size: $COMPRESSED_SIZE"
read -p "Delete compressed file to save space? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm "$COMPRESSED_FILE"
    echo "✓ Deleted $COMPRESSED_FILE"
fi

echo
echo "======================================================================="
echo "COMPLETE!"
echo "======================================================================="
echo
echo "✓ Address database ready: $OUTPUT_FILE"
echo
echo "Next step: python3 import_db.py"
echo
