"""Shared helpers for Claude's smoke harnesses (imported by framework-specific scripts)."""

from __future__ import annotations

import json
import math
import platform
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def data_dir(cfg) -> Path:
    return Path(cfg["work_root"]) / "smoke" / "data"


def write_json(obj, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, allow_nan=False, default=str), encoding="utf-8")


def cuda_memory(torch) -> dict:
    return {"max_allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "max_reserved_bytes": int(torch.cuda.max_memory_reserved()),
            "device_total_bytes": int(torch.cuda.get_device_properties(0).total_memory)}


def runtime(torch) -> dict:
    return {"python": sys.version.split()[0], "executable": sys.executable, "platform": platform.platform(),
            "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(), "device": torch.cuda.get_device_name(0),
            "capability": list(torch.cuda.get_device_capability(0))}


def finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def iteration_summary(iters) -> dict:
    """Median/first wall time and loss finiteness over recorded iterations."""
    times = [r["seconds"] for r in iters]
    later = sorted(times[1:]) or times
    return {"iterations": len(iters), "all_losses_finite": all(r["finite"] for r in iters),
            "first_iteration_seconds": times[0] if times else None,
            "median_seconds_after_first": later[len(later) // 2] if later else None,
            "total_seconds": sum(times)}


def failure(exc) -> dict:
    return {"error_type": type(exc).__name__, "error": str(exc)[:2000],
            "traceback_tail": traceback.format_exc()[-3000:]}


class Timer:
    def __init__(self, torch):
        self.torch = torch
        self.t0 = None

    def start(self):
        self.torch.cuda.synchronize()
        self.t0 = time.perf_counter()

    def stop(self) -> float:
        self.torch.cuda.synchronize()
        return time.perf_counter() - self.t0
