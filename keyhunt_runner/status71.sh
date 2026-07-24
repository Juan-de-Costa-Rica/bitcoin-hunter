#!/bin/bash
# Quick status for the puzzle 71 hunt.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
pos=$(cat checkpoint71.txt)
python3 - "$pos" <<'EOF'
import sys
pos = int(sys.argv[1], 16)
lo, hi = 2**70, 2**71
era_start = 0x6aaaaaab326f85a1bb  # keyhunt era began here, 2026-07-24
print(f"frontier:            0x{pos:x}")
print(f"position in range:   {(pos-lo)/(hi-lo)*100:.4f}% of [2^70, 2^71)")
scanned = pos - era_start
print(f"scanned (keyhunt):   {scanned:,} keys ({scanned/(hi-lo)*100:.6f}% of range)")
print(f"days remaining @1.8M/s: {(hi-pos)/1_810_000/86400:,.0f}")
EOF
echo "--- last 3 chunks:"
tail -3 hunt71.log 2>/dev/null
echo "--- process:"
pgrep -af "keyhunt -m address" || echo "NOT RUNNING"
