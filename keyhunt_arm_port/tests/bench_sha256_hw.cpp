#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include "sha256.h"   // declares sha256sse_1B (baseline NEON 4-way)

void sha256hw_1B(uint32_t*,uint32_t*,uint32_t*,uint32_t*,
                 unsigned char*,unsigned char*,unsigned char*,unsigned char*);

static double now() {
  struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts);
  return ts.tv_sec + ts.tv_nsec*1e-9;
}
static void hex(const uint8_t*d,char*o){ for(int i=0;i<32;i++) sprintf(o+2*i,"%02x",d[i]); o[64]=0; }

int main() {
  // --- Known-answer test: SHA-256("abc") padded single block ---
  uint32_t Wabc[16] = {0};
  Wabc[0]=0x61626380u; Wabc[15]=0x00000018u;
  const char* KAT="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
  uint8_t hw[32],ne[32]; char sh[65],sn[65];
  uint32_t z[16]={0};
  sha256hw_1B(Wabc,z,z,z, hw,ne,ne,ne); hex(hw,sh);
  sha256sse_1B(Wabc,z,z,z, ne,hw,hw,hw); hex(ne,sn);   // note: reuse buffers, lane0 is what matters
  printf("KAT abc:\n  expect %s\n  hw     %s  %s\n  neon   %s  %s\n",
         KAT, sh, strcmp(sh,KAT)?"FAIL":"ok", sn, strcmp(sn,KAT)?"FAIL":"ok");
  if(strcmp(sh,KAT)||strcmp(sn,KAT)) { printf("KAT FAILED - aborting\n"); return 1; }

  // --- Equivalence on random blocks (4 lanes) ---
  srand(12345);
  const int N=4096;
  uint32_t (*blk)[16]=(uint32_t(*)[16])malloc(sizeof(uint32_t)*16*N*4);
  for(int i=0;i<N*4;i++) for(int j=0;j<16;j++) blk[i][j]=((uint32_t)rand()<<16)^rand();
  int mism=0;
  uint8_t a0[32],a1[32],a2[32],a3[32], b0[32],b1[32],b2[32],b3[32];
  for(int i=0;i<N;i++){
    uint32_t*i0=blk[i*4],*i1=blk[i*4+1],*i2=blk[i*4+2],*i3=blk[i*4+3];
    sha256sse_1B(i0,i1,i2,i3, a0,a1,a2,a3);
    sha256hw_1B (i0,i1,i2,i3, b0,b1,b2,b3);
    if(memcmp(a0,b0,32)||memcmp(a1,b1,32)||memcmp(a2,b2,32)||memcmp(a3,b3,32)) mism++;
  }
  printf("Equivalence over %d blocks (x4 lanes): %s (%d mismatches)\n",
         N, mism?"FAIL":"PASS", mism);
  if(mism){ char x[65],y[65]; hex(a0,x); hex(b0,y);
    printf("  lane0 neon=%s\n  lane0 hw  =%s\n",x,y); return 1; }

  // --- Benchmark: hashes/sec (4 per call) ---
  const long ITER=3000000; // 3M calls = 12M hashes each
  volatile uint8_t sink=0;
  double t0=now();
  for(long k=0;k<ITER;k++){ uint32_t*b=blk[(k&1023)*4];
    sha256sse_1B(b,b+16,b+32,b+48, a0,a1,a2,a3); sink^=a0[0]; }
  double t1=now();
  for(long k=0;k<ITER;k++){ uint32_t*b=blk[(k&1023)*4];
    sha256hw_1B (b,b+16,b+32,b+48, b0,b1,b2,b3); sink^=b0[0]; }
  double t2=now();
  double neon=(ITER*4.0)/(t1-t0), hwr=(ITER*4.0)/(t2-t1);
  printf("NEON 4-way sha256sse_1B: %.2f Mhash/s\n", neon/1e6);
  printf("HW   sha256hw_1B       : %.2f Mhash/s\n", hwr/1e6);
  printf("Speedup: %.2fx  (sink=%d)\n", hwr/neon, sink);
  free(blk);
  return 0;
}
