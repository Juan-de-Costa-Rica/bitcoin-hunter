# ARM fast-engine benchmark

Oracle Cloud free tier, **Ampere Neoverse-N1** (aarch64), 4 vCPU. Both engines
measured in the **production config** (`-m address -b 71 -R -n 0x10000000`),
single thread, keyhunt's own stat-line counter, three stable 30s intervals
each. Same counter + same config on both, so the ~2x stat-line double-count
cancels in the ratio.

| Engine | keys/s (stat line, 1 thread) | notes |
|--------|------------------------------|-------|
| legacy (GMP, `gmp256k1/`)          | 1,218,833 | prior production engine |
| **ARM NEON fast (`secp256k1/` + sse2neon)** | **2,188,288** | this port |
| **speedup** | **1.80×** | |

Cross-check against the documented baseline: legacy single-thread stat = 1.22
M/s → ×3 threads ÷ ~2 (stat double-count) ≈ 1.81 M/s wall-clock, exactly the
figure recorded for the 3-thread legacy hunt. The ARM build therefore lifts the
deployed 3-thread hunt from ~1.81 to **~3.3 M/s wall-clock**.

## Why 1.8x and not the 3-5x first projected

The pre-port profile showed 58% of time in libgmp. The intuition was that
replacing GMP would be a big win. In practice **GMP's hand-tuned aarch64
assembly for 256-bit multiply/reduce is very good**, and the `__int128`-based
port of the VanitySearch field code roughly matches it rather than crushing it.
The real, measured win comes from the **4-way SIMD hash kernels** (SHA-256 +
RIPEMD-160 via sse2neon/NEON) replacing scalar OpenSSL hashing.

Paths to more, in rough order of effort/payoff, none pursued here:
- **ARMv8 SHA-256 crypto-extension instructions** (the N1 has `sha2`) instead of
  the software 4-way SHA. RIPEMD-160 has no hardware instruction and would
  remain the hash bottleneck, so the ceiling is modest.
- **libsecp256k1 assembly field** in place of the ported VanitySearch `Int`.
- **GPU** — the only route to order-of-magnitude gains; not available on this
  free-tier box.

## Bottom line

A clean, correctness-validated **1.8x**, close to the "2x is feasible" estimate.
It does not change the search odds in any meaningful way (see the project
README) — it runs because the Oracle box is free.

## Reproduce

```bash
# both binaries, production config, 1 thread, 30s intervals
cd /tmp
printf '1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU\n' > t.txt
for b in /home/opc/keyhunt-arm/keyhunt /home/opc/keyhunt/keyhunt.legacy.bak; do
  timeout 100 "$b" -m address -f t.txt -b 71 -l compress -t 1 -R -n 0x10000000 -s 30 \
    2>&1 | tr '\r' '\n' | grep -i 'Total.*seconds'
done
```
