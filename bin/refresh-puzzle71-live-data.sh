#!/bin/bash
# Feed for the public puzzle-71 live page (~/sites/puzzle71-live/data.json).
#
# Pulls the real hunt state off the Oracle box and writes the JSON the page
# reads. Runs on debian-langosta (isocrono rail), never on Oracle.
#
# KILL SWITCH: if a SOLUTION file exists on Oracle, this script publishes a
# dark feed (no keys, no rate) and stops. Per keyhunt_runner/SOLUTION-RUNBOOK.md
# the win must reach a private mempool before anything is public — the live
# page must not be the thing that tips off a sniper.
set -uo pipefail

OUT="${1:-$HOME/sites/puzzle71-live/data.json}"
TARGET_ADDRESS="1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
PRIZE_BTC="7.1"
# keyhunt's stat line double-counts keys by exactly 2x (see project memory).
STAT_DIVISOR=2

raw=$(ssh -o BatchMode=yes -o ConnectTimeout=15 oracle '
  cd /home/opc/bitcoin-hunter/keyhunt_runner || exit 9
  if ls SOLUTION_puzzle71_*.txt /home/opc/SOLUTION_puzzle71_*.txt >/dev/null 2>&1; then
    echo "SOLVED=1"; exit 0
  fi
  echo "SOLVED=0"
  pid=$(pgrep -f "keyhunt -m address -f puzzle71" | head -1)
  if [ -n "$pid" ]; then
    echo "RUNNING=1"
    # elapsed seconds, not lstart: Oracle is UTC and lstart carries no zone,
    # so parsing it locally shifts the start time by the offset.
    echo "ELAPSED=$(ps -o etimes= -p "$pid" | tr -d " ")"
  else
    echo "RUNNING=0"
  fi
  echo "STAT=$(grep -oE "Total [0-9]+ keys in [0-9]+ seconds" last_chunk.out 2>/dev/null | tail -1)"
  grep -oE "Base key: [0-9a-f]+" last_chunk.out 2>/dev/null | tail -8 | sed "s/Base key: /BASEKEY=/"
' 2>/dev/null)
ssh_rc=$?

now=$(date -Iseconds)

# Unreachable Oracle is not a solve — say "unknown", keep the page honest.
if [ $ssh_rc -ne 0 ] || [ -z "$raw" ]; then
  printf '{"generated_at":"%s","feed_ok":false,"solved":false,"running":false,"target_address":"%s","prize_btc":%s}\n' \
    "$now" "$TARGET_ADDRESS" "$PRIZE_BTC" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
  echo "feed: oracle unreachable (rc=$ssh_rc) — published degraded feed"
  exit 0
fi

if grep -q '^SOLVED=1' <<<"$raw"; then
  printf '{"generated_at":"%s","feed_ok":true,"solved":true,"running":false,"target_address":"%s","prize_btc":%s}\n' \
    "$now" "$TARGET_ADDRESS" "$PRIZE_BTC" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
  echo "feed: SOLUTION present — published dark feed, see SOLUTION-RUNBOOK.md"
  exit 0
fi

running=$(grep -oP '^RUNNING=\K.*' <<<"$raw" | head -1)
elapsed=$(grep -oP '^ELAPSED=\K.*' <<<"$raw" | head -1)
stat=$(grep -oP '^STAT=\K.*' <<<"$raw" | head -1)
total_stat=$(grep -oP 'Total \K[0-9]+' <<<"$stat")
seconds=$(grep -oP 'in \K[0-9]+' <<<"$stat")

keys_real=$(( ${total_stat:-0} / STAT_DIVISOR ))
rate_real=0
[ "${seconds:-0}" -gt 0 ] && rate_real=$(( keys_real / seconds ))

started_iso=""
[ -n "${elapsed:-}" ] && started_iso=$(date -Iseconds -d "@$(( $(date +%s) - elapsed ))")

# BTC price for the prize tile; a stale/failed fetch just omits it.
btc_usd=$(curl -s --max-time 10 https://blockchain.info/ticker \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["USD"]["last"])' 2>/dev/null || echo "")

base_keys=$(grep -oP '^BASEKEY=\K.*' <<<"$raw" \
  | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')

python3 - "$OUT" <<EOF
import json, sys
d = {
  "generated_at": "$now",
  "feed_ok": True,
  "solved": False,
  "running": ${running:-0} == 1,
  "run_started": "$started_iso" or None,
  "run_seconds": ${seconds:-0},
  "keys_this_run": $keys_real,
  "rate_keys_per_sec": $rate_real,
  "recent_base_keys": $base_keys,
  "target_address": "$TARGET_ADDRESS",
  "prize_btc": $PRIZE_BTC,
  "btc_usd": ${btc_usd:-None},
  "keyspace_bits": 71,
}
p = sys.argv[1]
open(p + ".tmp", "w").write(json.dumps(d, indent=2) + "\n")
import os; os.replace(p + ".tmp", p)
print("feed: ok — %.2f Mkeys/s, %.3e keys this run" % (d["rate_keys_per_sec"]/1e6, d["keys_this_run"]))
EOF
