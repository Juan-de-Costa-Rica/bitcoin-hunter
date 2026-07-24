// Tests keyhunt's SSE(->NEON) fast hash path in isolation:
// sha256sse_1B + ripemd160sse_32 on the k=1 pubkey, vs known hash160.
#include <cstdio>
#include <cstring>
#include <cstdint>
#include "hash/sha256.h"
#include "hash/ripemd160.h"

void sha256sse_1B(uint32_t *i0, uint32_t *i1, uint32_t *i2, uint32_t *i3,
                  unsigned char *d0, unsigned char *d1, unsigned char *d2, unsigned char *d3);

static void hex(const uint8_t *d, int n) { for (int i=0;i<n;i++) printf("%02x", d[i]); }

// X of k=1 pubkey, as Int bits[] words (bits[7]=high .. bits[0]=low)
static uint32_t Xbits[8] = {
  0x16f81798, 0x59f2815b, 0x2dce28d9, 0x029bfcdb,
  0xce870b07, 0x55a06295, 0xf9dcbbac, 0x79be667e };

#define KEYBUFFPREFIX(buff,bits,fix) \
buff[0] = (bits[7] >> 8) | ((uint32_t)(fix) << 24); \
buff[1] = (bits[6] >> 8) | (bits[7] <<24); \
buff[2] = (bits[5] >> 8) | (bits[6] <<24); \
buff[3] = (bits[4] >> 8) | (bits[5] <<24); \
buff[4] = (bits[3] >> 8) | (bits[4] <<24); \
buff[5] = (bits[2] >> 8) | (bits[3] <<24); \
buff[6] = (bits[1] >> 8) | (bits[2] <<24); \
buff[7] = (bits[0] >> 8) | (bits[1] <<24); \
buff[8] = 0x00800000 | (bits[0] <<24); \
buff[9]=0;buff[10]=0;buff[11]=0;buff[12]=0;buff[13]=0;buff[14]=0; \
buff[15] = 0x108;

int main() {
  uint32_t b0[16],b1[16],b2[16],b3[16];
  KEYBUFFPREFIX(b0, Xbits, 0x02);
  memcpy(b1,b0,64); memcpy(b2,b0,64); memcpy(b3,b0,64);

  unsigned char sh0[64],sh1[64],sh2[64],sh3[64];
  uint8_t h0[20],h1[20],h2[20],h3[20];
  sha256sse_1B(b0,b1,b2,b3, sh0,sh1,sh2,sh3);
  printf("sha256sse lane0 = "); hex(sh0,32);
  printf("\nexpected sha256 = 0f715baf5d4c2ed329785cef29e562f73488c8a2bb9dbc5700b361d54b9b0554\n");

  ripemd160sse_32(sh0,sh1,sh2,sh3, h0,h1,h2,h3);
  printf("hash160sse lane0= "); hex(h0,20);
  printf("\nexpected hash160= 751e76e8199196d454941c45d1b3a323f1433bd6\n");
  int ok = memcmp(h0,(const uint8_t*)"\x75\x1e\x76\xe8\x19\x91\x96\xd4\x54\x94\x1c\x45\xd1\xb3\xa3\x23\xf1\x43\x3b\xd6",20)==0;
  printf("SSE/NEON HASH PATH %s\n", ok?"OK":"BROKEN");
  return ok?0:1;
}
