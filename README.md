# Bitcoin Puzzle Solver

Educational project exploring Bitcoin's cryptographic security through the [Bitcoin Puzzle Challenge](https://privatekeys.pw/puzzles/bitcoin-puzzle-tx) - a series of increasingly difficult puzzles with real BTC prizes.

## Puzzle Solver (Main)

Targets specific Bitcoin puzzles with known address ranges. Currently hunting **Puzzle #71** (7.1 BTC / ~$675k prize).

### How It Works

1. Search a known key range (2^70 to 2^71 for Puzzle #71)
2. Generate public keys using elliptic curve math
3. Hash to Bitcoin address format (Hash160)
4. Compare against target address

### Performance

Optimized to **157,000 keys/sec** on Oracle Cloud free tier (ARM, 3 cores):

| Optimization | Rate | Improvement |
|--------------|------|-------------|
| Baseline | 28,630 k/s | - |
| PublicKey.from_valid_secret() | 56,267 k/s | +96% |
| Incremental point addition | 140,053 k/s | +389% |
| Direct FFI to libsecp256k1 | 157,000 k/s | +448% |

See [OPTIMIZATION_REPORT_2025-11-26.md](puzzle_solver/OPTIMIZATION_REPORT_2025-11-26.md) for details.

### Usage

```bash
cd puzzle_solver

# Run solver (3 workers, resume from checkpoint)
python3 puzzle_search.py 71 -w 3 --resume

# Check stats
python3 puzzle_stats.py 71
```

### Odds

After 1 year of 24/7 running: **1 in 238 million** (slightly better than Powerball!)

Expected time to solve: ~79 million years. But someone has to win eventually.

## Collision Scanner (Archived)

An alternative approach in `collision_scanner/` that generates random keys and checks against a database of all funded Bitcoin addresses.

**Why it's archived:** The odds are ~24 quintillion times worse than the puzzle solver. The puzzle constrains the search space to 2^70 keys; random collision hunting searches 2^160.

## Requirements

```bash
pip3 install coincurve
```

## Educational Value

- Elliptic curve cryptography (secp256k1)
- Bitcoin address derivation (Hash160 = RIPEMD160(SHA256(pubkey)))
- Why Bitcoin is cryptographically secure
- Performance optimization techniques (FFI, incremental point addition)

## Disclaimer

This is an educational project demonstrating Bitcoin's security. The probability of finding any solution is astronomically low - but the electricity is free on Oracle's free tier, so why not?
