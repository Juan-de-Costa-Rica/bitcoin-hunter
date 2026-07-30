
## 2026-07-30 — Hardware SHA-256 (ARMv8 crypto ext) for hash160

**Finding:** Oracle Neoverse-N1 exposes the `sha2` crypto extension (`/proc/cpuinfo`:
`aes pmull sha1 sha2`). The NEON port hashed with the software 4-way SSE→sse2neon
kernel and never used the hardware SHA-256 instructions. The prior project note
("would need ARMv8 SHA crypto-ext ... none on free tier") was wrong — it is available.

**Change:** New `sha256_hw.cpp` implements a single-block SHA-256 via
`vsha256hq_u32/…su0/…su1` intrinsics, matching keyhunt's `sha256sse_1B` contract
(16 native-endian schedule words in, big-endian 32-byte digest out). `sha256hw_1B`
runs it x4. Guarded by `__ARM_FEATURE_SHA2`; falls back to `sha256sse_1B` elsewhere.
SECP256K1.cpp hash160 paths call `sha256hw_1B`; Makefile `arm` target builds/links it.

**Validation (dev tree /home/opc/keyhunt-dev, live hunt untouched):**
- KAT SHA-256("abc") ✓ both kernels.
- Byte-identical to NEON over 4096×4 random blocks (0 mismatches).
- End-to-end: recovers puzzle keys 1,3,7,8,15,31,0x4c,0xe0,0x1d3,0x202,0x483,0xa7b,
  0x1460,0x2930 with correct compressed addresses.

**Speed (1 core, core-3, away from hunt):**
- SHA-256 kernel micro: 5.44 → 16.69 Mhash/s = 3.07x.
- Full keyhunt: 1,091,447 → 1,482,069 keys/s = **1.36x (~36%)** end-to-end.
- Projected 3-thread hunt: ~3.3 → ~4.5 Mkeys/s.

**Deploy status:** NOT deployed. Production binary /home/opc/keyhunt-arm/keyhunt still
the NEON build. Deploy = stop hunt, swap binary + source, restart. Pending Juan's go.

### Deployed to production 2026-07-30 ~20:40 UTC
- Stopped runner+hunt cleanly (gotcha: orphaned heartbeat `sleep 300` kept the
  flock fd 9 open after the wrapper died; had to kill it before hunt71.sh would
  re-acquire the single-instance lock).
- Backed up prior NEON binary -> /home/opc/keyhunt-arm/keyhunt.neon.bak
  (rollback: stop hunt, `cp keyhunt.neon.bak keyhunt`, relaunch). legacy.bak also intact.
- Deployed source into /home/opc/keyhunt-arm, rebuilt `make arm`, self-check OK.
- Relaunched via `setsid ./hunt71.sh`; keyhunt -t 3 -R live on new binary.
- Old in-flight regions (abandoned, EV-neutral): 4f1916.., 62de14.., 5876eb..
  New regions: 74ef82.., 781588.., 55f571.. (fresh, no overlap).
- No work lost: random mode has no checkpoint; solution-save logic (SOLUTION_*.txt
  + Kuma DOWN ping) intact; runner-dir KEYFOUND clean.

## Profile-driven roadmap (2026-07-30, deployed binary, perf)
Hot path GetHash160_fromX = 51% of thread time:
  - ripemd160sse_32 (RIPEMD-160, sse2neon 4-way): **32%**  <- now #1 hotspot
  - sha256hw_1B (hardware SHA-256): 18%  <- already optimized, leave it
IntGroup::ModInv + ModMulK1 (field math): ~12%
Remainder: EC point adds / endomorphism bookkeeping.

Re-prioritized levers:
  #2 RIPEMD-160: no ARM hardware instr exists; kernel is already 4-way SIMD.
     sse2neon already lowers to native NEON, so a hand rewrite likely nets only
     ~10-15% on RIPEMD = ~3-5% end-to-end. LOW value.
  #3 Field math (ModMulK1 __int128): hand-tuned UMULH/MUL, marginal (~1-3% e2e).
  DROP: generic "multi-buffer SHA" — SHA is only 18% now, not worth it.
Strategic note: hardware SHA was the one lever with a real HW backing (3x).
Everything left is software-SIMD-bound with small end-to-end payoff. Given
P(solve/yr)=1-in-8.4M, further micro-opt is exercise, not expected value.

## 2026-07-30 — RIPEMD-160 lever: tried, NOT deployed (negative result)
Specialized `ripemd160opt_32`: hardcode the 8 constant padding words (w8=0x80,
w9-13=0, w14=0x100, w15=0) instead of per-lane LOADW gathers, drop the dead
padding memcpys, keep all 160 rounds verbatim. Let -Ofast fold the +0/+const adds.
- Correctness: byte-identical to deployed ripemd160sse_32 over 4096x4 random blocks.
- Speed: 8.89 -> 9.14 Mhash/s = **1.028x (2.8%)** = <1% end-to-end. NOT worth deploying.
- Why: RIPEMD-160 is latency-bound (serial round dependency a->a->a x80 x2 lines),
  not op-count-bound. Removing ~80 adds + 8 gathers barely touches the critical path;
  the compiler already folded most constants at -Ofast. 4-way SIMD fills NEON width
  but the per-lane chain latency dominates.
- Only path to real RIPEMD gain: 8-way SIMD (2 NEON regs/var) to hide more latency.
  High effort + risk, ~5-6% e2e best case. Odds (1-in-8.4M/yr) don't justify it.
- Artifact kept: experimental_ripemd160_opt.cpp + tests/bench_ripemd160_opt.cpp (NOT
  in the build). Campaign conclusion: hardware SHA (+36%) was the one real lever; done.
