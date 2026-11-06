"""Record complete environment pins for the smoke interpreters (Claude, G0 prerequisite).

  python scripts/smoke/env_pins.py --out-dir configs/smoke/env

Writes ``<name>_freeze.txt`` (``uv pip freeze``) per interpreter and ``env_pins.json``
with OS, driver, CUDA/cuDNN and framework versions. Read-only for every environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ENVS = {
    "det_eval_ultralytics": "C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe",
    "rtdetrv2": "C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe",
}
PROBE = r"""
import json, sys, platform
import torch, torchvision
out = {"python": sys.version, "platform": platform.platform(), "torch": torch.__version__,
       "torchvision": torchvision.__version__, "cuda_runtime": torch.version.cuda,
       "cudnn": torch.backends.cudnn.version(), "cuda_available": torch.cuda.is_available(),
       "device": torch.cuda.get_device_name(0), "capability": list(torch.cuda.get_device_capability(0)),
       "arch_list": torch.cuda.get_arch_list()}
for mod in ("ultralytics", "numpy", "scipy", "faster_coco_eval", "pycocotools", "PIL", "cv2"):
    try:
        m = __import__(mod)
        out[mod] = getattr(m, "__version__", "present")
    except Exception as exc:
        out[mod] = f"absent ({type(exc).__name__})"
print(json.dumps(out))
"""


def text(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    a = p.parse_args(argv)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    pins = {"recorded_by": "Claude", "host_os": platform.platform(), "os_version": platform.version(),
            "nvidia_smi": text(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,vbios_version",
                                "--format=csv,noheader"]),
            "uv": text(["uv", "--version"]), "environments": {}}
    for name, python in ENVS.items():
        freeze = text(["uv", "pip", "freeze", "--python", python])
        path = a.out_dir / f"{name}_freeze.txt"
        path.write_text(freeze + "\n", encoding="utf-8")
        info = json.loads(text([python, "-I", "-c", PROBE]))
        info.update({"interpreter": python, "freeze_file": path.name,
                     "freeze_sha256": hashlib.sha256((freeze + "\n").encode()).hexdigest(),
                     "package_count": len(freeze.splitlines())})
        pins["environments"][name] = info
    pins["environments"]["det_eval_ultralytics"]["policy"] = (
        "existing det-eval-2d venv used read-only; nothing installed; freeze compared before/after the smoke")
    pins["environments"]["rtdetrv2"]["policy"] = (
        "new uv venv outside Git: uv venv --python 3.12; uv pip install --index-url "
        "https://download.pytorch.org/whl/cu128 --extra-index-url https://pypi.org/simple "
        "--index-strategy unsafe-best-match torch==2.11.0+cu128 torchvision==0.26.0+cu128 "
        "'faster-coco-eval>=1.6.6' PyYAML tensorboard scipy packaging pycocotools "
        "(onnx/onnxruntime-gpu from requirements.txt omitted: export-only)")
    (a.out_dir / "env_pins.json").write_text(json.dumps(pins, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in pins.items() if k != "environments"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
