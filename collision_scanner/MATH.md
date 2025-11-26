# Bitcoin Address Hunter - The Math

## Address Space

**Total possible Bitcoin addresses:** 2^160 ≈ 1.46 × 10^48

This is approximately:
- 1,461,501,637,330,902,918,203,684,832,716,283,019,655,932,542,976 addresses
- Or in words: 1.46 quindecillion addresses

## Funded Addresses

### Current Balances (as of 2024-2025)
- **~40-50 million** addresses currently have BTC > 0
- These are addresses with active balances right now

### Historical Addresses (WHAT WE NEED)
- **~200-300 million** addresses have EVER received Bitcoin
- This includes:
  - Current funded addresses (~50M)
  - Addresses that had funds but are now empty (~150-250M)
  - Addresses from historical transactions

**For this project, we want addresses that CURRENTLY have funds (40-50M)**

This is the "lottery" approach - only checking winning tickets that still have prizes!

## Oracle Server Performance

From our test run:

### Key Generation Speed
- **775 keys per second**
- Each key generates **3 addresses**:
  1. P2PKH compressed (legacy, starts with "1")
  2. P2PKH uncompressed (legacy, starts with "1")
  3. P2WPKH (SegWit, starts with "bc1")

### Total Address Checking Speed
- **2,325 addresses per second** (775 keys × 3 addresses)

### Database Lookup Speed
- **148,000 lookups per second**
- Database is NOT the bottleneck (63x faster than needed)

## The Bottleneck

**Key generation (cryptography)** is the limiting factor at 775 keys/sec, not database lookups.

## Do We Batch?

**Currently: NO batching needed** because:
- We generate: 2,325 addresses/sec
- Database can handle: 148,000 lookups/sec
- Database is 63x faster than we need

**If we optimize key generation** (multi-threading, C/Rust), then batching would help.

## The Probability Math

### With 50 Million Funded Addresses

```
Probability per address = 50,000,000 / 1.46 × 10^48
                        = 3.42 × 10^-42
                        = 0.00000000000000000000000000000000000000000342
```

### Performance Over Time

| Timeframe | Addresses Checked |
|-----------|-------------------|
| 1 second  | 2,325 |
| 1 minute  | 139,500 |
| 1 hour    | 8,370,000 |
| 1 day     | 200,880,000 |
| 1 year    | 73,321,200,000 |
| 1 century | 7,332,120,000,000 |

### Expected Time to Find One Address

```
Expected checks needed = 1 / probability
                       = 1 / (3.42 × 10^-42)
                       = 2.92 × 10^41 addresses

Time required = 2.92 × 10^41 / 2,325 addresses/sec
              = 1.26 × 10^38 seconds
              = 3.99 × 10^30 years
```

**For comparison:**
- Age of the universe: 1.38 × 10^10 years
- Time until heat death of universe: ~10^100 years
- Time to find funded address: 3.99 × 10^30 years

**You would need to run the scanner for 289 BILLION BILLION BILLION times the age of the universe.**

## With 300 Million Historical Addresses

```
Probability = 300,000,000 / 1.46 × 10^48 = 2.05 × 10^-41

Expected time = 1 / (2.05 × 10^-41 × 2,325)
              = 2.1 × 10^38 seconds
              = 6.65 × 10^30 years
```

Still impossibly long, just 6x better odds.

## Optimization Potential

### Current: Single-threaded Python
- 775 keys/sec on 4 ARM cores
- Only using ~1 core effectively

### Multi-threaded Python
- Estimated: 2,000-3,000 keys/sec (all 4 cores)

### Compiled Language (C/Rust)
- Estimated: 10,000-50,000 keys/sec
- With GPU acceleration: 1,000,000+ keys/sec

### With 1 Million keys/sec
```
Time to find funded address = 1.26 × 10^38 / (1,000,000 × 3)
                            = 4.2 × 10^31 seconds
                            = 1.33 × 10^24 years
```

Still 100 trillion trillion times the age of the universe.

## Storage Requirements for Full Database

### 50 Million Current Funded Addresses (RECOMMENDED)
- Each address: ~35 bytes (address string)
- Raw data: 50M × 35 = 1.75 GB
- With SQLite indexes: **~4-6 GB**

**Oracle server free space:** 9 GB on root partition ✅ **This fits!**

### Alternative: 300 Million Historical Addresses
- Raw data: 300M × 35 = 10.5 GB
- With SQLite indexes: ~20-25 GB
- **Problem:** Doesn't fit on Oracle server
- **Also:** Wastes space on empty addresses (no lottery prize!)

## Conclusion

**For the "lottery" approach, we need ~50 million currently funded addresses.**

This will:
- Fit on Oracle server (4-6 GB database)
- Only check addresses that actually have prizes
- Still demonstrate the massive keyspace

Even with 50 million funded addresses, the probability is so astronomically low that you will NEVER find a funded address through random generation.

**This is precisely why Bitcoin is secure!**

The project's educational value is in:
1. Learning how Bitcoin cryptography works
2. Understanding the massive keyspace (1.46 × 10^48 addresses)
3. Seeing real-time how secure Bitcoin actually is
4. Learning database optimization for fast lookups
5. Appreciating that even with 50M "winning tickets", finding one randomly takes 10^30 years

But you will never, ever find a funded address randomly. The math is clear.

### Quick Summary

- **Total addresses:** 1.46 × 10^48
- **Funded addresses:** ~50 million
- **Your speed:** 2,325 addresses/sec
- **Expected time to find one:** 3.99 × 10^30 years (289 billion billion billion × age of universe)
- **Batching:** Not needed, database is 63x faster than key generation
- **Storage needed:** 4-6 GB (fits on Oracle server)
