# Bitcoin Address Hunter

Educational project to demonstrate Bitcoin's keyspace security by randomly generating private keys and checking against a local database of funded addresses.

## How It Works

1. **Download Address Database** - Get list of all Bitcoin addresses with balances
2. **Import to SQLite** - Build indexed local database for fast lookups
3. **Generate Keys** - Create random Bitcoin private keys
4. **Derive Addresses** - Generate Legacy (P2PKH), SegWit, and Bech32 addresses
5. **Check Database** - Query local database (no API calls needed)
6. **Track Stats** - Monitor keys/second, total checked, runtime

## Reality Check

There are 2^160 (~1.4 × 10^48) possible Bitcoin addresses. Even with 50 million funded addresses, the probability of finding one randomly is:

**1 in 29,000,000,000,000,000,000,000,000,000,000,000,000,000**

This project demonstrates why Bitcoin's cryptography is secure!

## Setup

```bash
# Install dependencies
pip3 install -r requirements.txt

# Download address database
python3 download_addresses.py

# Import to SQLite (this may take a while)
python3 import_db.py

# Run the scanner
python3 scanner.py
```

## Database Sources

- Blockchair daily dumps (updated daily)
- Bitcoin address balance lists
- ~40-50 million addresses with transaction history

## Storage Requirements

- Address database: ~10-15GB
- Logs: minimal (<100MB)

## Performance

Expected on Oracle ARM (4 cores, 24GB RAM):
- Database lookups: 100,000+ per second
- Key generation: 10,000-50,000 per second
- Overall: 5,000-10,000 addresses checked per second

## Output

The scanner displays:
- Keys generated per second
- Total addresses checked
- Runtime
- Any funded addresses found (will never happen via random generation)

## Educational Value

This project teaches:
- Bitcoin private/public key cryptography (secp256k1)
- Address derivation (P2PKH, P2WPKH, Bech32)
- The massive scale of Bitcoin's keyspace
- Database optimization for fast lookups
- Why Bitcoin is cryptographically secure
