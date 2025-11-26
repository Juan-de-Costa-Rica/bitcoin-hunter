#!/usr/bin/env python3
"""
Bitcoin cryptography utilities for key generation and address derivation.
"""

import hashlib
import os
import base58
from ecdsa import SigningKey, SECP256k1


def generate_private_key():
    """Generate a random 256-bit Bitcoin private key."""
    return os.urandom(32)


def private_key_to_wif(private_key, compressed=True):
    """Convert private key to Wallet Import Format (WIF)."""
    # Add version byte (0x80 for mainnet)
    extended = b'\x80' + private_key

    # Add compression flag if compressed
    if compressed:
        extended += b'\x01'

    # Double SHA256 for checksum
    checksum = hashlib.sha256(hashlib.sha256(extended).digest()).digest()[:4]

    # Encode to base58
    return base58.b58encode(extended + checksum).decode('ascii')


def private_key_to_public_key(private_key, compressed=True):
    """Derive public key from private key using secp256k1."""
    sk = SigningKey.from_string(private_key, curve=SECP256k1)
    vk = sk.get_verifying_key()

    if compressed:
        # Compressed public key: 02/03 + x coordinate
        x = vk.pubkey.point.x()
        y = vk.pubkey.point.y()
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        return prefix + x.to_bytes(32, byteorder='big')
    else:
        # Uncompressed: 04 + x + y
        return b'\x04' + vk.to_string()


def hash160(data):
    """Perform SHA256 followed by RIPEMD160 (standard Bitcoin hash)."""
    sha256_hash = hashlib.sha256(data).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    return ripemd160.digest()


def public_key_to_address_p2pkh(public_key):
    """
    Convert public key to Legacy P2PKH address (starts with 1).
    This is the original Bitcoin address format.
    """
    # Hash160 of public key
    pubkey_hash = hash160(public_key)

    # Add version byte (0x00 for mainnet)
    versioned = b'\x00' + pubkey_hash

    # Calculate checksum (double SHA256)
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]

    # Encode to base58
    return base58.b58encode(versioned + checksum).decode('ascii')


def public_key_to_address_p2wpkh(public_key):
    """
    Convert compressed public key to Native SegWit address (starts with bc1).
    Bech32 encoding.
    """
    # SegWit uses compressed public keys only
    pubkey_hash = hash160(public_key)

    # Bech32 encoding (witness version 0)
    # Converting to bech32 format
    witver = 0
    witprog = pubkey_hash

    # Bech32 character set
    charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    def bech32_polymod(values):
        GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for v in values:
            b = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ v
            for i in range(5):
                chk ^= GEN[i] if ((b >> i) & 1) else 0
        return chk

    def bech32_hrp_expand(hrp):
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    def bech32_create_checksum(hrp, data):
        values = bech32_hrp_expand(hrp) + data
        polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
        return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

    def convertbits(data, frombits, tobits, pad=True):
        acc = 0
        bits = 0
        ret = []
        maxv = (1 << tobits) - 1
        max_acc = (1 << (frombits + tobits - 1)) - 1
        for value in data:
            acc = ((acc << frombits) | value) & max_acc
            bits += frombits
            while bits >= tobits:
                bits -= tobits
                ret.append((acc >> bits) & maxv)
        if pad:
            if bits:
                ret.append((acc << (tobits - bits)) & maxv)
        return ret

    # Convert to 5-bit groups
    five_bit_data = convertbits(witprog, 8, 5)

    # Combine witness version and program
    data = [witver] + five_bit_data

    # Create checksum
    hrp = "bc"  # mainnet
    checksum = bech32_create_checksum(hrp, data)

    # Encode
    combined = data + checksum
    return hrp + "1" + "".join([charset[d] for d in combined])


def generate_all_addresses(private_key):
    """
    Generate all address types from a private key.
    Returns dict with private_key (WIF), public_key (hex), and addresses.
    """
    # Generate public key (compressed for modern addresses)
    public_key_compressed = private_key_to_public_key(private_key, compressed=True)
    public_key_uncompressed = private_key_to_public_key(private_key, compressed=False)

    # Generate addresses
    addresses = {
        'private_key_wif': private_key_to_wif(private_key, compressed=True),
        'public_key_hex': public_key_compressed.hex(),
        'p2pkh_compressed': public_key_to_address_p2pkh(public_key_compressed),
        'p2pkh_uncompressed': public_key_to_address_p2pkh(public_key_uncompressed),
        'p2wpkh_bech32': public_key_to_address_p2wpkh(public_key_compressed),
    }

    return addresses


if __name__ == "__main__":
    # Test key generation
    print("Generating test Bitcoin key...\n")

    privkey = generate_private_key()
    result = generate_all_addresses(privkey)

    print(f"Private Key (hex): {privkey.hex()}")
    print(f"Private Key (WIF): {result['private_key_wif']}")
    print(f"Public Key: {result['public_key_hex']}")
    print(f"\nAddresses:")
    print(f"  P2PKH (compressed):   {result['p2pkh_compressed']}")
    print(f"  P2PKH (uncompressed): {result['p2pkh_uncompressed']}")
    print(f"  P2WPKH (bech32):      {result['p2wpkh_bech32']}")
