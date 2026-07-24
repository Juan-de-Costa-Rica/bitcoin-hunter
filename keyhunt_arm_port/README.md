# keyhunt ARM64 (NEON) fast-engine port

Ports [albertobsd/keyhunt](https://github.com/albertobsd/keyhunt)'s **fast**
`default` engine to aarch64, replacing the ~3x slower GMP `legacy` build the
Puzzle-71 hunt had been using on the Oracle Neoverse-N1 box.

Upstream is pinned at commit `2134a20` ("Remove telegram link").

## Why

keyhunt ships two engines:

- `legacy` — 256-bit field math via **libgmp** (`gmp256k1/`), scalar OpenSSL
  hashing. Portable, so it built on ARM. Slow: heap `mpz` ops, division-based
  modular reduction, per-key `mpz_export` conversions dominate the profile.
- `default` — a custom VanitySearch-derived field implementation
  (`secp256k1/Int.cpp`, batched Montgomery inversion) plus **4-way SSE**
  SHA-256 / RIPEMD-160 hash kernels. Much faster, but written for x86-64
  (`emmintrin.h`, `_addcarry_u64`, `mulq`/`shrdq` inline asm, `__m128i`).

On aarch64 the fast engine simply didn't compile, so the project settled for
`legacy`. This port makes the fast engine build and run correctly on ARM.

## What was changed (see `patches/`)

1. **`secp256k1/Int.h`** — added an `__aarch64__` branch providing the five
   x86 scalar intrinsics the `Int` class needs (`_umul128`, `__shiftright128`,
   `__shiftleft128`, `_addcarry_u64`, `_subborrow_u64`) implemented with the
   compiler's native `unsigned __int128`. Semantics (and positional argument
   order) match Intel's intrinsics exactly, since callers invoke them
   positionally.
2. **`secp256k1/Int.cpp`, `IntMod.cpp`** — guarded the vestigial
   `#include <emmintrin.h>` behind an x86 check (the scalar intrinsics now come
   from `Int.h`; neither file uses `__m128i` directly).
3. **`hash/sha256_sse.cpp`, `hash/ripemd160_sse.cpp`** — swapped
   `<immintrin.h>` for **sse2neon** on ARM. Every SSE intrinsic these kernels
   use is SSE2/SSSE3, all covered by sse2neon (NEON translation).
4. **`hash/sha256.cpp`, `hash/ripemd160.cpp`** — the scalar rotate helpers used
   x86 `rorl`/`roll` inline asm; added portable C rotates for non-x86.
5. **`Makefile`** — new `arm` target: the `default` recipe plus
   **`-fno-strict-aliasing`** (see below).

## The load-bearing bug: strict aliasing at `-Ofast`

After everything compiled, the ARM binary scanned at full speed but **found
nothing** — even keys 1–32 from `tests/1to32.txt`. Bisecting the pipeline with
isolated harnesses (`ssetest.cpp`) showed:

- EC math: correct pubkeys.
- `sha256sse_1B` (NEON): correct SHA-256.
- `ripemd160sse_32` (NEON): returned `0123456789abcdef…` — the RIPEMD-160
  **initial vector, byte-swapped and unchanged**. The compression function was
  a no-op.

Root cause: keyhunt's SSE hash code type-puns the `__m128i` state through
`(uint32_t *)&s[0]` (the `DEPACK` / `LOADW` macros). That violates strict
aliasing, and GCC at `-Ofast` (which enables `-fstrict-aliasing`) on aarch64
reorders/elides the state stores, so RIPEMD never leaves its init state. On
x86-64 the same UB happened to survive; on ARM it doesn't.

Fix: build with `-fno-strict-aliasing` — the standard remedy for this class of
crypto code (the Linux kernel and many hash libraries build this way). With it,
the NEON hash path produces the exact correct `hash160`.

## Validation

Two independent oracles, both must pass before deploy:

- **`gen_ref.py`** — a self-contained pure-Python secp256k1 → compressed
  P2PKH implementation (no deps). Sanity-checked against the canonical
  `privkey=1` address `1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH`.
- **`tests/1to32.txt`** — keyhunt's shipped known-key addresses. The fixed
  binary recovers 24 of them in ~20s (`-r 1:FFFFFFFF`), matching the trusted
  `legacy` binary key-for-key.

`ssetest.cpp` / `hashtest.cpp` bisect the hash layers directly against the
known `hash160` of the `privkey=1` pubkey (`751e76e8…3bd6`).

## Build

```bash
./build-arm.sh [DEST]          # default DEST=/home/opc/keyhunt-arm
```

Clones upstream at the pinned commit, fetches `sse2neon.h`, applies the
patches, installs the `arm` target, builds, and runs the self-test.

## Benchmark

See `BENCHMARK.md` for the measured wall-clock speedup over the `legacy`
engine on the Oracle Neoverse-N1 (single-thread, fixed-range traversal).
