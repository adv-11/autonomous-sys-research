#!/bin/bash
# Claude Opus: detached remote queue A (setup + 1-epoch throughput pilot).
# Invokes the frozen remote.py stages unchanged; stops at the first failure.
E=/content/evidence
mkdir -p $E
cd /content
run() {  # name, args...
  local name=$1; shift
  echo "$(date -u +%FT%TZ) START $name" >> $E/queue.log
  if python3 -u /content/packet/remote.py "$@" > $E/$name.log 2>&1; then
    echo "$(date -u +%FT%TZ) PASS $name" >> $E/queue.log
  else
    echo "$(date -u +%FT%TZ) FAIL $name rc=$?" >> $E/queue.log
    touch $E/QUEUE_FAIL; exit 1
  fi
}
run setup setup
run pilot train --arm pilot --epochs 1
touch $E/QUEUE_A_DONE
