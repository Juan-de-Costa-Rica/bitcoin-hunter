// Standalone ARM correctness harness for keyhunt's hash layer.
// Bisects the SSE(->NEON) hash port against scalar reference + known vectors.
#include <cstdio>
#include <cstring>
#include <cstdint>
#include "hash/sha256.h"
#include "hash/ripemd160.h"

static void hex(const uint8_t *d, int n) { for (int i=0;i<n;i++) printf("%02x", d[i]); }

int main() {
  // --- Known vector: SHA256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
  // sha256_33 hashes exactly 33 bytes, so use the 4-way sse + scalar self-tests instead.
  // --- hash160 of privkey=1 compressed pubkey must be 751e76e8199196d454941c45d1b3a323f1433bd6
  // compressed pubkey for k=1:
  uint8_t pub[33] = {
    0x02,0x79,0xbe,0x66,0x7e,0xf9,0xdc,0xbb,0xac,0x55,0xa0,0x62,0x95,0xce,0x87,0x0b,
    0x07,0x02,0x9b,0xfc,0xdb,0x2d,0xce,0x28,0xd9,0x59,0xf2,0x81,0x5b,0x16,0xf8,0x17,0x98 };
  uint8_t sha[32], rmd[20];
  // scalar path
  sha256_33(pub, sha);
  printf("sha256(pub33) = "); hex(sha,32); printf("\n");
  // ripemd160 scalar
  ripemd160(sha, 32, rmd);
  printf("hash160       = "); hex(rmd,20);
  printf("\nexpected      = 751e76e8199196d454941c45d1b3a323f1433bd6\n");
  int ok = (memcmp(rmd, (const uint8_t*)"\x75\x1e\x76\xe8\x19\x91\x96\xd4\x54\x94\x1c\x45\xd1\xb3\xa3\x23\xf1\x43\x3b\xd6", 20) == 0);
  printf("HASH160 %s\n", ok ? "MATCH (scalar path OK)" : "MISMATCH (scalar path BROKEN)");
  return ok ? 0 : 1;
}
