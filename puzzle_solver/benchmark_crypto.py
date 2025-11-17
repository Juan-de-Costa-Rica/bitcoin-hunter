#!/usr/bin/env python3
"""Benchmark ecdsa vs coincurve performance on ARM64."""

import time
import secrets


def benchmark_ecdsa():
    """Benchmark current ecdsa library."""
    from ecdsa import SigningKey, SECP256k1
    import hashlib
    import base58

    iterations = 1000
    start = time.time()

    for _ in range(iterations):
        private_key_bytes = secrets.token_bytes(32)
        sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
        vk = sk.get_verifying_key()

        # Get compressed public key (same as puzzle_search.py does)
        pubkey_point = vk.pubkey.point
        x = pubkey_point.x()
        y = pubkey_point.y()

        if y % 2 == 0:
            pubkey_compressed = b'\x02' + x.to_bytes(32, 'big')
        else:
            pubkey_compressed = b'\x03' + x.to_bytes(32, 'big')

        # Hash160
        sha256_hash = hashlib.sha256(pubkey_compressed).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

    elapsed = time.time() - start
    return iterations / elapsed


def benchmark_coincurve():
    """Benchmark coincurve library."""
    from coincurve import PrivateKey
    import hashlib

    iterations = 1000
    start = time.time()

    for _ in range(iterations):
        private_key_bytes = secrets.token_bytes(32)
        privkey = PrivateKey(private_key_bytes)

        # Get compressed public key
        pubkey_compressed = privkey.public_key.format(compressed=True)

        # Hash160
        sha256_hash = hashlib.sha256(pubkey_compressed).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

    elapsed = time.time() - start
    return iterations / elapsed


if __name__ == "__main__":
    print("="*70)
    print("Crypto Library Performance Benchmark (ARM64)")
    print("="*70)
    print()
    print("Testing 1000 iterations of:")
    print("  - Private key generation")
    print("  - Public key derivation (compressed)")
    print("  - Hash160 (SHA256 + RIPEMD160)")
    print()
    print("Running benchmarks...")
    print()

    # Run ecdsa benchmark
    print("1. Testing ecdsa (pure Python)...")
    ecdsa_rate = benchmark_ecdsa()
    print(f"   Result: {ecdsa_rate:,.0f} keys/sec")
    print()

    # Run coincurve benchmark
    print("2. Testing coincurve (libsecp256k1 C library)...")
    coincurve_rate = benchmark_coincurve()
    print(f"   Result: {coincurve_rate:,.0f} keys/sec")
    print()

    # Calculate speedup
    speedup = coincurve_rate / ecdsa_rate
    print("="*70)
    print(f"Speedup: {speedup:.1f}x faster with coincurve!")
    print("="*70)
    print()

    # Estimate real-world performance
    print("Estimated solver performance with 3 workers:")
    print(f"  Current (ecdsa):   ~{ecdsa_rate * 3:,.0f} keys/sec")
    print(f"  With coincurve:    ~{coincurve_rate * 3:,.0f} keys/sec")
    print(f"  Performance gain:  +{(coincurve_rate - ecdsa_rate) * 3:,.0f} keys/sec")
    print()
