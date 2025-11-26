# Bitcoin Puzzle Solver Optimization Report

**Date:** 2025-11-26  
**Baseline:** 28,630 keys/sec (3 workers)  
**After Optimization:** 56,267 keys/sec (3 workers)  
**Improvement:** +96.5% (~2x speedup)

---

## Summary

Two key optimizations were identified and implemented through careful profiling:

1. **PublicKey.from_valid_secret()** - Major optimization (+100%)
2. **Reduced stop_event checking frequency** - Minor optimization (+3.4%)

---

## Optimization 1: PublicKey.from_valid_secret()

### Problem
The original code created a full PrivateKey object, then extracted the public key:
```python
privkey = CoincurvePrivateKey(private_key_bytes)
pubkey_compressed = privkey.public_key.format(compressed=True)
```

### Solution
Since we only need the public key (not the private key object), use the direct constructor:
```python
pubkey_compressed = CoincurvePublicKey.from_valid_secret(private_key_bytes).format(compressed=True)
```

### Benchmark Results
| Method | Keys/sec | Improvement |
|--------|----------|-------------|
| PrivateKey() then .public_key | 9,562 | baseline |
| PublicKey.from_valid_secret() | 19,161 | +100.4% |

### Technical Explanation
- PrivateKey() performs additional validation and object setup
- from_valid_secret() skips validation (we know keys are valid in our search range)
- Directly computes public key without intermediate PrivateKey wrapper

---

## Optimization 2: Reduced Stop Event Check Frequency

### Problem
The worker loop checked `stop_event.is_set()` on every iteration:
```python
while current_key < end_key and not self.stop_event.is_set():
```

This causes IPC overhead on every key check.

### Solution
Check stop signal every 1000 iterations instead:
```python
while current_key < end_key:
    stop_check_counter += 1
    if stop_check_counter >= STOP_CHECK_INTERVAL:
        stop_check_counter = 0
        if self.stop_event.is_set():
            break
```

### Benchmark Results
| Check Frequency | Keys/sec | Improvement |
|-----------------|----------|-------------|
| Every iteration | 18,571 | baseline |
| Every 1000 | 19,211 | +3.4% |

---

## Git Commits

```
0a14dff perf: Use PublicKey.from_valid_secret for 2x speedup
00e006d perf: Reduce stop_event check frequency for +3.4% speedup
```

---

## Rejected Optimizations

The following were tested but not implemented:

1. **Function inlining** - Marginal gain (~2%) but reduces code readability
2. **NumPy batch processing** - Coincurve doesn't support batch operations
3. **Alternative libraries** - fastecdsa not available on ARM64
4. **keyhunt (C tool)** - Uses x86-specific SIMD (SSE), incompatible with ARM64

---

## System Information

- **Server:** Oracle Cloud ARM (4 cores, using 3)
- **Crypto Library:** coincurve (libsecp256k1 bindings)
- **Python:** 3.x
- **Architecture:** aarch64 (ARM64)

---

## Final Performance

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Single core | ~9,500 k/s | ~19,000 k/s | +100% |
| 3 workers | 28,630 k/s | 56,267 k/s | +96.5% |

