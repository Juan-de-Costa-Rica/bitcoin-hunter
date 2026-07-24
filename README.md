# Bitcoin Puzzle Solver

Educational project exploring Bitcoin's cryptographic security through the [Bitcoin Puzzle Challenge](https://privatekeys.pw/puzzles/bitcoin-puzzle-tx) - a series of increasingly difficult puzzles with real BTC prizes.

## Current Engine: keyhunt (2026-07)

The Python solver below has been retired as the production engine. The hunt now
runs [albertobsd/keyhunt](https://github.com/albertobsd/keyhunt) (C + GMP,
`legacy` build for ARM) driven by `keyhunt_runner/hunt71.sh`:

- **1.81 Mkeys/s sustained on 3 cores** — 11.5x the Python solver's 157k/s
  (keyhunt's own stats line double-counts; the 1.81M figure is wall-clock
  verified: 300M-key range in 166s)
- Correctness validated: found solved Puzzle #66's known key, plus 3 planted
  keys at start/middle/end of a test range (no coverage gaps; final block
  rounds up, never truncates)
- Chunked checkpointing: `checkpoint71.txt` advances only after a ~2h chunk
  completes, fixing the old resume bug where 2 of 3 workers lost all progress
  on every reboot (checkpoint stored only the global max key)
- Started 2026-07-24 from the Python era's frontier `0x6aaaaaab326f85a1bb`
- `keyhunt_runner/status71.sh` prints frontier, rate, and process health
- Cron `@reboot` relaunches the wrapper; solutions land in
  `SOLUTION_puzzle71_<ts>.txt` (runner dir + `$HOME`)

### Usage

```bash
cd keyhunt_runner

# Start the hunt (backgrounded; resumes from checkpoint71.txt)
nohup ./hunt71.sh >/dev/null 2>&1 &

# Check frontier, rate, and process health
./status71.sh
```

### Odds

At 1.81 Mkeys/s, one year of 24/7 searching covers 57.1 trillion keys out of
the 2^70 keyspace — about **1 in 20.7 million** odds of finding the key
(4.84 × 10⁻⁸). That is ~14x better than a single Powerball ticket
(1 in 292 million), and 11.5x better than the retired Python engine's
1-in-238-million. Expected time to solve at this rate: ~20.7 million years.

The odds are what they are because the keyspace is enormous, not because the
engine is slow. No CPU optimization meaningfully changes the outcome — this
runs because the Oracle free tier costs nothing.

### Monitoring / notifications

Two Uptime Kuma monitors on debian-langosta (both wired to the Telegram
notification), so nobody has to babysit the box:

- **`puzzle71-heartbeat`** (id 25, push) — the hunt pings Kuma every 5 min
  (`hb()` in `hunt71.sh`, reaching Kuma over Tailscale via `curl --resolve`).
  If the pings stop for ~30 min — crash, reboot, **or a solve** (keyhunt exits
  on a win) — Kuma flips DOWN and alerts. On a confirmed solve the wrapper also
  sends an explicit DOWN ping with the private key in the message.
- **`puzzle71-prize-balance`** (id 26, keyword) — Kuma polls
  `blockchain.info/q/addressbalance/<prize-addr>` every 5 min with the current
  balance as the keyword. The moment anyone sweeps the address (us after a win,
  or a stranger who solves it first), the keyword vanishes and Kuma alerts.

No bespoke watcher script — both are stock Kuma monitors.

## Puzzle Solver (Python, retired 2026-07)

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

### Odds (at the retired 157k/s rate)

After 1 year of 24/7 running: **1 in 238 million**. Superseded by the keyhunt
engine above (1 in 20.7 million/year). Kept here for historical context.

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
