#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include "ripemd160.h"   // declares ripemd160sse_32 (deployed baseline)

void ripemd160opt_32(unsigned char*,unsigned char*,unsigned char*,unsigned char*,
                     unsigned char*,unsigned char*,unsigned char*,unsigned char*);

static double now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}

int main(){
  srand(9001);
  const int N=4096;
  // 64-byte buffers per lane (baseline writes padding into 32..63)
  static uint8_t A[N][4][64], B[N][4][64];
  for(int i=0;i<N;i++) for(int l=0;l<4;l++){
    for(int j=0;j<32;j++){ uint8_t r=rand(); A[i][l][j]=r; B[i][l][j]=r; }
    memset(A[i][l]+32,0,32); memset(B[i][l]+32,0,32);
  }
  // --- equivalence ---
  int mism=0; uint8_t a0[20],a1[20],a2[20],a3[20], b0[20],b1[20],b2[20],b3[20];
  for(int i=0;i<N;i++){
    ripemd160sse_32(A[i][0],A[i][1],A[i][2],A[i][3], a0,a1,a2,a3);
    ripemd160opt_32(B[i][0],B[i][1],B[i][2],B[i][3], b0,b1,b2,b3);
    if(memcmp(a0,b0,20)||memcmp(a1,b1,20)||memcmp(a2,b2,20)||memcmp(a3,b3,20)) mism++;
  }
  printf("Equivalence over %d blocks (x4 lanes): %s (%d mismatches)\n", N, mism?"FAIL":"PASS", mism);
  if(mism){ char x[41],y[41]; for(int k=0;k<20;k++){sprintf(x+2*k,"%02x",a0[k]);sprintf(y+2*k,"%02x",b0[k]);}
    printf("  lane0 base=%s\n  lane0 opt =%s\n",x,y); return 1; }

  // --- benchmark (4 hashes per call). refill first 32 bytes cheaply from index ---
  const long ITER=3000000;
  volatile uint8_t sink=0;
  double t0=now();
  for(long k=0;k<ITER;k++){ uint8_t*b=A[k&1023][0];
    ripemd160sse_32(b,b+64,b+128,b+192, a0,a1,a2,a3); sink^=a0[0]; }
  double t1=now();
  for(long k=0;k<ITER;k++){ uint8_t*b=B[k&1023][0];
    ripemd160opt_32(b,b+64,b+128,b+192, b0,b1,b2,b3); sink^=b0[0]; }
  double t2=now();
  double base=(ITER*4.0)/(t1-t0), opt=(ITER*4.0)/(t2-t1);
  printf("baseline ripemd160sse_32: %.2f Mhash/s\n", base/1e6);
  printf("opt      ripemd160opt_32: %.2f Mhash/s\n", opt/1e6);
  printf("Speedup: %.3fx  (sink=%d)\n", opt/base, sink);
  return 0;
}
