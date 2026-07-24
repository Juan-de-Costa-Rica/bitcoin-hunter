#!/bin/bash
# Reproducible build of the ARM64 (NEON) fast keyhunt for the Puzzle-71 hunt.
#
# keyhunt's fast `default` engine (custom secp256k1 field math + 4-way SSE
# hashing, VanitySearch-derived) is x86-only upstream; on aarch64 the project
# fell back to the ~3x slower GMP `legacy` build. This script rebuilds the fast
# engine on ARM by:
#   1. porting the x86 scalar intrinsics in secp256k1/Int.h to __int128 + NEON,
#   2. translating the SSE hash kernels via sse2neon,
#   3. building with -fno-strict-aliasing (the SSE hash code type-puns through
#      __m128i; GCC -Ofast miscompiles it on aarch64 without this flag, leaving
#      RIPEMD-160 stuck at its init vector — see README).
#
# Result on Oracle Neoverse-N1: correct hash160 pipeline, validated against
# tests/1to32.txt and an independent pure-Python secp256k1 oracle (gen_ref.py).
set -euo pipefail

UPSTREAM=https://github.com/albertobsd/keyhunt.git
PIN=2134a2024e524775b13f82aa1fa07b1c8053f867   # "Remove telegram link"
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-/home/opc/keyhunt-arm}"

echo "[*] Cloning keyhunt @ ${PIN:0:7} -> $DEST"
rm -rf "$DEST"
git clone -q "$UPSTREAM" "$DEST"
git -C "$DEST" checkout -q "$PIN"

echo "[*] Fetching sse2neon.h"
if [ -f "$HERE/sse2neon.h" ]; then
  cp "$HERE/sse2neon.h" "$DEST/sse2neon.h"
else
  curl -sSL -o "$DEST/sse2neon.h" \
    https://raw.githubusercontent.com/DLTcollab/sse2neon/master/sse2neon.h
fi
cp "$DEST/sse2neon.h" "$DEST/hash/sse2neon.h"

echo "[*] Applying ARM port patches"
declare -A MAP=(
  [secp256k1_Int.h.patch]=secp256k1/Int.h
  [secp256k1_Int.cpp.patch]=secp256k1/Int.cpp
  [secp256k1_IntMod.cpp.patch]=secp256k1/IntMod.cpp
  [hash_sha256.cpp.patch]=hash/sha256.cpp
  [hash_ripemd160.cpp.patch]=hash/ripemd160.cpp
  [hash_sha256_sse.cpp.patch]=hash/sha256_sse.cpp
  [hash_ripemd160_sse.cpp.patch]=hash/ripemd160_sse.cpp
)
for p in "${!MAP[@]}"; do
  patch -s "$DEST/${MAP[$p]}" < "$HERE/patches/$p"
done

echo "[*] Installing arm Makefile target"
cp "$HERE/Makefile.arm-target" "$DEST/Makefile.arm"
cat "$DEST/Makefile.arm" >> "$DEST/Makefile"

echo "[*] Building (make arm)"
( cd "$DEST" && make arm )

echo "[*] Self-test: recover puzzle keys from tests/1to32.txt"
( cd "$DEST" && rm -f KEYFOUNDKEYFOUND.txt \
  && timeout 25 ./keyhunt -m address -f tests/1to32.txt -r 1:FFFFFFFF -l compress -t 1 >/dev/null 2>&1 || true
  n=$(grep -cE "Private Key" KEYFOUNDKEYFOUND.txt 2>/dev/null || echo 0)
  echo "    recovered $n keys (expect >=20)"
  [ "$n" -ge 20 ] && echo "[✓] BUILD VALID" || { echo "[✗] SELF-TEST FAILED"; exit 1; } )
