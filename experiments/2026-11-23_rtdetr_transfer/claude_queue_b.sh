#!/bin/bash
# Claude Opus: detached remote queue B. Usage: claude_queue_b.sh BASELINE_EPOCHS ADAPT_EPOCHS
# Epoch counts come only from the committed throughput plan. Stops at first failure.
E=/content/evidence
B=$1; A=$2
cd /content
run() {
  local name=$1; shift
  echo "$(date -u +%FT%TZ) START $name" >> $E/queue.log
  if python3 -u /content/packet/remote.py "$@" > $E/$name.log 2>&1; then
    echo "$(date -u +%FT%TZ) PASS $name" >> $E/queue.log
  else
    echo "$(date -u +%FT%TZ) FAIL $name rc=$?" >> $E/queue.log
    touch $E/QUEUE_FAIL; exit 1
  fi
}
run baseline train --arm baseline --epochs $B
python3 - <<'EOF' || { echo "$(date -u +%FT%TZ) FAIL baseline_update_fraction" >> $E/queue.log; A=0; }
import json; s = json.load(open('/content/evidence/baseline_summary.json'))
assert s['successful_updates'] >= 0.95 * s['attempted_updates'], s
EOF
if [ "$A" -gt 0 ]; then run adaptation train --arm adaptation --epochs $A; fi
run infer_baseline infer --arm baseline
if [ "$A" -gt 0 ]; then run infer_adaptation infer --arm adaptation; fi
touch $E/QUEUE_B_DONE
