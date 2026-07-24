#!/bin/bash
# Puzzle 71 hunter — keyhunt RANDOM mode over the whole [2^70, 2^71) range.
#
# Why random, not sequential: the key was placed uniformly at random, and a
# solo CPU covers a negligible fraction either way, so sequential vs random is
# EV-identical. Random (keyhunt's default) spreads our coverage across the
# entire range instead of grinding the crowded low end that every default-config
# searcher starts on, and it needs no checkpoint — there is no contiguous
# progress to resume; every launch just keeps sampling. keyhunt runs until it
# finds the key or is killed; this wrapper only restarts it if it dies.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
KEYHUNT=/home/opc/keyhunt-arm/keyhunt
THREADS=3                    # keep 1 of 4 cores free for Caddy etc.
NSEQ=0x10000000              # sequential run length after each random hop
cd "$DIR"

# Uptime Kuma heartbeat (monitor id 25, push). Oracle can't resolve the
# tsdproxy DNS name and Kuma routes by SNI, so --resolve pins name->IP. Silence
# >~30min (Kuma interval 600s x retries) flips the monitor DOWN and pings
# Telegram — covering BOTH "hunt died" and "hunt solved & exited".
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
( while :; do hb up "random hunt puzzle71 (3 threads)"; sleep 300; done ) &
HB_PID=$!
trap 'kill "$HB_PID" 2>/dev/null' EXIT

while :; do
  t0=$(date +%s)
  "$KEYHUNT" -m address -f puzzle71.txt -b 71 -l compress \
    -t $THREADS -R -n "$NSEQ" -s 300 > last_chunk.out 2>&1
  rc=$?
  if [ -s KEYFOUNDKEYFOUND.txt ]; then
    ts=$(date +%Y%m%d-%H%M%S)
    cp KEYFOUNDKEYFOUND.txt "SOLUTION_puzzle71_${ts}.txt"
    cp KEYFOUNDKEYFOUND.txt "/home/opc/SOLUTION_puzzle71_${ts}.txt"
    echo "$(date -Is) *** SOLUTION FOUND *** -> SOLUTION_puzzle71_${ts}.txt" >> hunt71.log
    # Loud, immediate signal: flip the heartbeat DOWN with the key in the msg.
    hb down "SOLVED puzzle71 $(grep -m1 -i 'Private Key' KEYFOUNDKEYFOUND.txt)"
    exit 0
  fi
  el=$(( $(date +%s) - t0 ))
  # keyhunt in -R mode runs forever; reaching here means it died (crash, OOM,
  # kill). Restart with a short backoff. A too-fast exit loop just logs.
  echo "$(date -Is) keyhunt exited rc=$rc after ${el}s (no solution) — restart in 30s" >> hunt71.log
  sleep 30
done
