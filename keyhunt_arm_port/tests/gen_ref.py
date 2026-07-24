#!/usr/bin/env python3
"""Independent secp256k1 -> compressed P2PKH oracle for validating the ARM
keyhunt port. Pure Python, no external deps. Prints "<privhex> <address>" pairs
so a test can plant the address, run keyhunt over a range containing the key,
and confirm it recovers the private key.
"""
import hashlib, sys

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def inv(a, m): return pow(a, m - 2, m)

def add(p, q):
    if p is None: return q
    if q is None: return p
    if p[0] == q[0] and (p[1] + q[1]) % P == 0: return None
    if p == q:
        l = (3 * p[0] * p[0]) * inv(2 * p[1], P) % P
    else:
        l = (q[1] - p[1]) * inv(q[0] - p[0], P) % P
    x = (l * l - p[0] - q[0]) % P
    y = (l * (p[0] - x) - p[1]) % P
    return (x, y)

def mul(k):
    r = None; a = (Gx, Gy)
    while k:
        if k & 1: r = add(r, a)
        a = add(a, a); k >>= 1
    return r

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58check(payload):
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    n = int.from_bytes(payload + chk, "big")
    s = ""
    while n: n, r = divmod(n, 58); s = B58[r] + s
    return "1" * (len(payload + chk) - len((payload + chk).lstrip(b"\0"))) + s

def address(priv):
    x, y = mul(priv)
    pub = bytes([2 + (y & 1)]) + x.to_bytes(32, "big")
    h = hashlib.new("ripemd160", hashlib.sha256(pub).digest()).digest()
    return b58check(b"\x00" + h)

if __name__ == "__main__":
    for hx in sys.argv[1:]:
        k = int(hx, 16)
        print(f"{k:x} {address(k)}")
