#!/bin/bash
# Health check for the puzzle 71 random-mode hunt (run on Oracle).
# Random mode has no contiguous progress to report; what matters is that
# keyhunt is alive, its rate, and that no solution/steal has fired.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
echo "=== process ==="
pgrep -af "keyhunt -m address -f puzzle71" | grep -v pgrep || echo "NOT RUNNING"
echo "=== rate (last stats line) ==="
grep -oE "\(.* keys/s\)" last_chunk.out 2>/dev/null | tail -1 || echo "no stats yet"
echo "=== solutions on disk ==="
ls -1 SOLUTION_puzzle71_*.txt /home/opc/SOLUTION_puzzle71_*.txt 2>/dev/null || echo "none (good — still hunting)"
echo "=== recent wrapper log ==="
tail -3 hunt71.log 2>/dev/null || echo "(no log entries — normal until a restart/solve)"
echo "=== load ==="
uptime | grep -o "load average.*"
