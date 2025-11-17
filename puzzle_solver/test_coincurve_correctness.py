#!/usr/bin/env python3
"""Test that coincurve produces same addresses as ecdsa."""

import hashlib
import base58


def test_key_to_address(test_key_int):
    """Test that both libraries produce the same address."""
    private_key_bytes = test_key_int.to_bytes(32, 'big')

    # Method 1: ecdsa (old)
    from ecdsa import SigningKey, SECP256k1
    sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
    vk = sk.get_verifying_key()
    pubkey_point = vk.pubkey.point
    x1 = pubkey_point.x()
    y1 = pubkey_point.y()

    if y1 % 2 == 0:
        pubkey_compressed1 = b'\x02' + x1.to_bytes(32, 'big')
    else:
        pubkey_compressed1 = b'\x03' + x1.to_bytes(32, 'big')

    sha256_hash1 = hashlib.sha256(pubkey_compressed1).digest()
    ripemd160_hash1 = hashlib.new('ripemd160', sha256_hash1).digest()
    versioned1 = b'\x00' + ripemd160_hash1
    checksum1 = hashlib.sha256(hashlib.sha256(versioned1).digest()).digest()[:4]
    address1 = base58.b58encode(versioned1 + checksum1).decode('ascii')

    # Method 2: coincurve (new)
    from coincurve import PrivateKey as CoincurvePrivateKey
    privkey = CoincurvePrivateKey(private_key_bytes)
    pubkey_compressed2 = privkey.public_key.format(compressed=True)

    pubkey_uncompressed = privkey.public_key.format(compressed=False)
    x2 = int.from_bytes(pubkey_uncompressed[1:33], 'big')
    y2 = int.from_bytes(pubkey_uncompressed[33:65], 'big')

    sha256_hash2 = hashlib.sha256(pubkey_compressed2).digest()
    ripemd160_hash2 = hashlib.new('ripemd160', sha256_hash2).digest()
    versioned2 = b'\x00' + ripemd160_hash2
    checksum2 = hashlib.sha256(hashlib.sha256(versioned2).digest()).digest()[:4]
    address2 = base58.b58encode(versioned2 + checksum2).decode('ascii')

    return address1, address2, (x1, y1), (x2, y2)


if __name__ == "__main__":
    print("="*70)
    print("Testing coincurve correctness")
    print("="*70)
    print()

    # Test with known keys
    test_cases = [
        (1, "Satoshi's first key"),
        (2**70, "Puzzle #71 range start"),
        (2**71 - 1, "Puzzle #71 range end"),
        (0x123456789abcdef0, "Random test key 1"),
        (0xfedcba9876543210, "Random test key 2"),
    ]

    all_passed = True
    for key_int, description in test_cases:
        addr1, addr2, (x1, y1), (x2, y2) = test_key_to_address(key_int)

        if addr1 == addr2 and x1 == x2 and y1 == y2:
            print(f"✅ PASS: {description}")
            print(f"   Key: 0x{key_int:x}")
            print(f"   Address: {addr1}")
            print()
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Key: 0x{key_int:x}")
            print(f"   ecdsa address: {addr1}")
            print(f"   coincurve address: {addr2}")
            print()
            all_passed = False

    print("="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED! coincurve produces identical addresses to ecdsa")
    else:
        print("❌ TESTS FAILED! Address mismatch detected")
    print("="*70)
