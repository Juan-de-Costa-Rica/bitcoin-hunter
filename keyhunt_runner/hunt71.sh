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

# Uptime Kuma heartbeat (monitor id 25, push type). Oracle can't resolve the
# tsdproxy DNS name and Kuma routes by SNI, so --resolve pins name->IP. Silence
# for >~30min (Kuma interval 600s x retries) flips the monitor DOWN and pings
# Telegram — which covers BOTH "hunt died" and "hunt solved & exited".
KUMA_HOST=kuma.mink-gopher.ts.net
KUMA_IP=100.95.201.87
KUMA_TOKEN=wuz6g1LVmI
hb() {  # hb <status> [msg]
  curl -sS -o /dev/null --max-time 15 --resolve "$KUMA_HOST:443:$KUMA_IP" \
    "https://$KUMA_HOST/api/push/$KUMA_TOKEN?status=${1}&msg=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "${2:-ok}")" 2>/dev/null || true
}

# Single-instance guard: cron @reboot + a manual start must never run two
# hunts (6 threads would blow the 3-core budget). flock holds fd 9 for the
# whole process; a second launch exits immediately.
exec 9>"$DIR/hunt71.lock"
if ! flock -n 9; then
  echo "$(date -Is) another hunt71 already running — exiting" >> hunt71.log
  exit 0
fi

# Background heartbeat: ping Kuma every 5min while this process lives. Dies with
# the wrapper (trap), so if the hunt stops for any reason the pings stop too.
( while :; do hb up "hunting @ $(cat "$DIR/checkpoint71.txt" 2>/dev/null)"; sleep 300; done ) &
HB_PID=$!
trap 'kill "$HB_PID" 2>/dev/null' EXIT

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
    # Loud, immediate signal: flip the heartbeat DOWN with the key in the msg.
    hb down "SOLVED puzzle71 $(grep -m1 -i 'Private Key' KEYFOUNDKEYFOUND.txt)"
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
