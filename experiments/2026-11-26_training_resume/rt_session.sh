#!/bin/bash
# Claude Opus: RT-DETR stage launcher (RT-DETR amendment 2).
# Usage: rt_session.sh A   |   rt_session.sh B BASE_EPOCHS ADAPT_EPOCHS
# Creates an isolated CPython 3.12 venv once, then runs the frozen queue scripts unchanged.
E=/content/evidence; mkdir -p $E
if [ ! -x /content/rtvenv/bin/python ]; then
  echo "$(date -u +%FT%TZ) START venv" >> $E/queue.log
  command -v uv >/dev/null || pip install -q uv > $E/uv_install.log 2>&1
  if uv venv --seed --python 3.12 /content/rtvenv > $E/venv.log 2>&1; then
    echo "$(date -u +%FT%TZ) PASS venv $(/content/rtvenv/bin/python -V 2>&1)" >> $E/queue.log
  else
    echo "$(date -u +%FT%TZ) FAIL venv" >> $E/queue.log; touch $E/QUEUE_FAIL; exit 1
  fi
fi
export PATH=/content/rtvenv/bin:$PATH
if [ "$1" = A ]; then exec bash /content/packet/claude_queue_a.sh; fi
exec bash /content/packet/claude_queue_b.sh "$2" "$3"
