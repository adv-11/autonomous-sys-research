#!/bin/bash
# Claude Opus: install the pinned Ultralytics into Colab's system Python and record the environment.
set -e
pip install -q ultralytics==8.4.197
python3 - <<'PY'
import sys, torch, ultralytics
print(sys.version, torch.__version__, ultralytics.__version__, torch.cuda.get_device_name(0))
PY
