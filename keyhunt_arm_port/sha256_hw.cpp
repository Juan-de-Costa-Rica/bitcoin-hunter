// ARMv8 hardware SHA-256 (Cryptography Extension) drop-in for keyhunt's
// 4-way sha256sse_1B. Same contract: each input iN points to 16 uint32
// message-schedule words (native-endian VALUE order, as keyhunt builds them,
// no input byteswap); each output dN receives a 32-byte big-endian digest.
//
// Requires -march=armv8-a+crypto (or +sha2). Neoverse-N1 (Oracle Ampere A1)
// exposes the sha2 feature. On any target WITHOUT the SHA2 extension this
// forwards to the portable NEON/SSE kernel, so the symbol is always safe.
#include "sha256.h"
#include <stdint.h>
#include <string.h>

#if defined(__aarch64__) && (defined(__ARM_FEATURE_SHA2) || defined(__ARM_FEATURE_CRYPTO))
#define KEYHUNT_HAVE_HW_SHA256 1
#include <arm_neon.h>
#endif

#ifdef KEYHUNT_HAVE_HW_SHA256

namespace _sha256hw {

static const uint32_t K[64] = {
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

static const uint32_t IV[8] = {
  0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
};

// One 64-byte block. W = 16 schedule words already in host VALUE order.
static inline void block(const uint32_t *W, uint8_t *digest) {
  uint32x4_t STATE0 = vld1q_u32(&IV[0]); // a b c d
  uint32x4_t STATE1 = vld1q_u32(&IV[4]); // e f g h
  const uint32x4_t ABEF_SAVE = STATE0;
  const uint32x4_t CDGH_SAVE = STATE1;

  // Schedule words are already the correct big-endian VALUES (keyhunt does not
  // byteswap on input), so load them straight -- no vrev32q_u8.
  uint32x4_t MSG0 = vld1q_u32(W + 0);
  uint32x4_t MSG1 = vld1q_u32(W + 4);
  uint32x4_t MSG2 = vld1q_u32(W + 8);
  uint32x4_t MSG3 = vld1q_u32(W + 12);

  uint32x4_t TMP0, TMP1, TMP2;

  TMP0 = vaddq_u32(MSG0, vld1q_u32(&K[0]));

  // Rounds 0-3
  MSG0 = vsha256su0q_u32(MSG0, MSG1);
  TMP2 = STATE0;
  TMP1 = vaddq_u32(MSG1, vld1q_u32(&K[4]));
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);
  MSG0 = vsha256su1q_u32(MSG0, MSG2, MSG3);

  // Rounds 4-7
  TMP0 = vaddq_u32(MSG2, vld1q_u32(&K[8]));
  MSG1 = vsha256su0q_u32(MSG1, MSG2);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);
  MSG1 = vsha256su1q_u32(MSG1, MSG3, MSG0);

  // Rounds 8-11
  TMP1 = vaddq_u32(MSG3, vld1q_u32(&K[12]));
  MSG2 = vsha256su0q_u32(MSG2, MSG3);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);
  MSG2 = vsha256su1q_u32(MSG2, MSG0, MSG1);

  // Rounds 12-15
  TMP0 = vaddq_u32(MSG0, vld1q_u32(&K[16]));
  MSG3 = vsha256su0q_u32(MSG3, MSG0);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);
  MSG3 = vsha256su1q_u32(MSG3, MSG1, MSG2);

  // Rounds 16-19
  TMP1 = vaddq_u32(MSG1, vld1q_u32(&K[20]));
  MSG0 = vsha256su0q_u32(MSG0, MSG1);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);
  MSG0 = vsha256su1q_u32(MSG0, MSG2, MSG3);

  // Rounds 20-23
  TMP0 = vaddq_u32(MSG2, vld1q_u32(&K[24]));
  MSG1 = vsha256su0q_u32(MSG1, MSG2);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);
  MSG1 = vsha256su1q_u32(MSG1, MSG3, MSG0);

  // Rounds 24-27
  TMP1 = vaddq_u32(MSG3, vld1q_u32(&K[28]));
  MSG2 = vsha256su0q_u32(MSG2, MSG3);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);
  MSG2 = vsha256su1q_u32(MSG2, MSG0, MSG1);

  // Rounds 28-31
  TMP0 = vaddq_u32(MSG0, vld1q_u32(&K[32]));
  MSG3 = vsha256su0q_u32(MSG3, MSG0);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);
  MSG3 = vsha256su1q_u32(MSG3, MSG1, MSG2);

  // Rounds 32-35
  TMP1 = vaddq_u32(MSG1, vld1q_u32(&K[36]));
  MSG0 = vsha256su0q_u32(MSG0, MSG1);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);
  MSG0 = vsha256su1q_u32(MSG0, MSG2, MSG3);

  // Rounds 36-39
  TMP0 = vaddq_u32(MSG2, vld1q_u32(&K[40]));
  MSG1 = vsha256su0q_u32(MSG1, MSG2);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);
  MSG1 = vsha256su1q_u32(MSG1, MSG3, MSG0);

  // Rounds 40-43
  TMP1 = vaddq_u32(MSG3, vld1q_u32(&K[44]));
  MSG2 = vsha256su0q_u32(MSG2, MSG3);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);
  MSG2 = vsha256su1q_u32(MSG2, MSG0, MSG1);

  // Rounds 44-47
  TMP0 = vaddq_u32(MSG0, vld1q_u32(&K[48]));
  MSG3 = vsha256su0q_u32(MSG3, MSG0);
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);
  MSG3 = vsha256su1q_u32(MSG3, MSG1, MSG2);

  // Rounds 48-51
  TMP1 = vaddq_u32(MSG1, vld1q_u32(&K[52]));
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);

  // Rounds 52-55
  TMP0 = vaddq_u32(MSG2, vld1q_u32(&K[56]));
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);

  // Rounds 56-59
  TMP1 = vaddq_u32(MSG3, vld1q_u32(&K[60]));
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP0);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP0);

  // Rounds 60-63
  TMP2 = STATE0;
  STATE0 = vsha256hq_u32(STATE0, STATE1, TMP1);
  STATE1 = vsha256h2q_u32(STATE1, TMP2, TMP1);

  STATE0 = vaddq_u32(STATE0, ABEF_SAVE);
  STATE1 = vaddq_u32(STATE1, CDGH_SAVE);

  // Digest is state words a..h, each stored big-endian.
  uint32_t out[8];
  vst1q_u32(&out[0], STATE0);
  vst1q_u32(&out[4], STATE1);
  for (int i = 0; i < 8; i++) {
    digest[i*4+0] = (uint8_t)(out[i] >> 24);
    digest[i*4+1] = (uint8_t)(out[i] >> 16);
    digest[i*4+2] = (uint8_t)(out[i] >> 8);
    digest[i*4+3] = (uint8_t)(out[i]);
  }
}

} // namespace

// Drop-in replacement for the 4-way NEON kernel.
void sha256hw_1B(uint32_t *i0, uint32_t *i1, uint32_t *i2, uint32_t *i3,
                 unsigned char *d0, unsigned char *d1,
                 unsigned char *d2, unsigned char *d3) {
  _sha256hw::block(i0, d0);
  _sha256hw::block(i1, d1);
  _sha256hw::block(i2, d2);
  _sha256hw::block(i3, d3);
}

#else  // no hardware SHA-256: forward to the portable kernel

void sha256hw_1B(uint32_t *i0, uint32_t *i1, uint32_t *i2, uint32_t *i3,
                 unsigned char *d0, unsigned char *d1,
                 unsigned char *d2, unsigned char *d3) {
  sha256sse_1B(i0, i1, i2, i3, d0, d1, d2, d3);
}

#endif
