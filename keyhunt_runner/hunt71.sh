#!/bin/bash
# Puzzle 71 hunter — keyhunt engine with chunked checkpointing.
# Scans [checkpoint, 2^71) in ~2h chunks; checkpoint advances only after a
# chunk completes cleanly, so a crash/reboot re-scans at most one chunk.
# keyhunt rounds the last block of a chunk UP (overshoot, never a gap), so
# back-to-back chunks have zero coverage holes.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
KEYHUNT=/home/opc/keyhunt/keyhunt
END_HEX=800000000000000000   # 2^71, exclusive
CHUNK=$((0x300000000))       # 12.9G keys ≈ 2h at 1.8 Mkeys/s
THREADS=3                    # keep 1 of 4 cores free for Caddy etc.
cd "$DIR"

while :; do
  pos=$(cat checkpoint71.txt)
  if [ "$((0x$pos))" -ge "$((0x$END_HEX))" ]; then
    echo "$(date -Is) RANGE EXHAUSTED at $pos" >> hunt71.log
    exit 0
  fi
  next=$(python3 -c "print(format(min(0x$pos + $CHUNK, 0x$END_HEX), 'x'))")
  t0=$(date +%s)
  "$KEYHUNT" -m address -f puzzle71.txt -r "$pos:$next" -l compress \
    -t $THREADS -n 16777216 -s 300 > last_chunk.out 2>&1
  rc=$?
  if [ -s KEYFOUNDKEYFOUND.txt ]; then
    ts=$(date +%Y%m%d-%H%M%S)
    cp KEYFOUNDKEYFOUND.txt "SOLUTION_puzzle71_${ts}.txt"
    cp KEYFOUNDKEYFOUND.txt "/home/opc/SOLUTION_puzzle71_${ts}.txt"
    echo "$(date -Is) *** SOLUTION FOUND *** in $pos:$next -> SOLUTION_puzzle71_${ts}.txt" >> hunt71.log
    exit 0
  fi
  el=$(( $(date +%s) - t0 ))
  if [ $rc -ne 0 ]; then
    echo "$(date -Is) keyhunt rc=$rc after ${el}s at $pos — retry in 60s, checkpoint NOT advanced" >> hunt71.log
    sleep 60
    continue
  fi
  if [ $el -lt 600 ]; then
    echo "$(date -Is) chunk $pos:$next finished suspiciously fast (${el}s) — pause 300s, checkpoint NOT advanced" >> hunt71.log
    sleep 300
    continue
  fi
  echo "$(date -Is) done $pos:$next ${el}s ~$(( CHUNK / el )) keys/s" >> hunt71.log
  printf '%s' "$next" > checkpoint71.txt.tmp && mv checkpoint71.txt.tmp checkpoint71.txt
done
