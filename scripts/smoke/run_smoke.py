"""Drive Claude's full model-feasibility smoke and collect raw results (G0 prerequisite).

  <any python>=3.11> scripts/smoke/run_smoke.py --config configs/smoke/smoke_config.json [--models ...]

For each model: ascending batch probes (each a fresh process, ``probe_iterations``
steps) until the fit rule fails; the 20-step run at the largest fitting batch;
evaluation of the official checkpoint on the 50 images at the primary and the
sensitivity cap; and one reference-evaluator CLI run in diagnostic mode. Each
framework runs in its own interpreter (see ``--ultralytics-python`` and
``--rtdetrv2-python``). Outputs go to <work_root>/smoke/results (outside Git).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))

from threshold_transfer import smoke  # noqa: E402
from threshold_transfer.metrics import ReferenceEvaluator  # noqa: E402
from threshold_transfer.schema import load_json  # noqa: E402

ULTRA = "C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe"
RTDETR = "C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe"


def run(cmd, log):
    with open(log, "a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(map(str, cmd)) + "\n")
        f.flush()
        proc = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=REPO)
    return proc.returncode


def harness(model_key, cfg, args):
    if cfg["models"][model_key]["framework"] == "ultralytics":
        return [args.ultralytics_python, "-I", HERE / "ultralytics_smoke.py"], ["--model", model_key]
    return [args.rtdetrv2_python, "-I", HERE / "rtdetrv2_smoke.py"], []


def train_model(model_key, cfg, args, results, log):
    base, extra = harness(model_key, cfg, args)
    probes = []
    chosen = None
    for batch in cfg["batch_candidates"]:
        out = results / f"probe_{model_key}_b{batch}.json"
        code = run(base + ["train", "--config", args.config, *extra, "--batch", batch,
                           "--iterations", cfg["probe_iterations"], "--out", out], log)
        rec = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"status": "FAIL", "error": f"exit {code}"}
        probes.append({"batch": batch, "status": rec["status"], "fits_rule": rec.get("fits_rule", False),
                       "max_reserved_bytes": rec.get("memory", {}).get("max_reserved_bytes"),
                       "max_allocated_bytes": rec.get("memory", {}).get("max_allocated_bytes"),
                       "error": rec.get("error")})
        if not rec.get("fits_rule"):
            break
        chosen = batch
    final = None
    if chosen is not None:
        out = results / f"train_{model_key}_b{chosen}_i{cfg['iterations']}.json"
        run(base + ["train", "--config", args.config, *extra, "--batch", chosen,
                    "--iterations", cfg["iterations"], "--out", out], log)
        final = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"status": "FAIL"}
    return {"probes": probes, "chosen_batch": chosen, "final": final}


def eval_model(model_key, cfg, args, results, log):
    base, extra = harness(model_key, cfg, args)
    evals = {}
    for cap in (cfg["candidate_policy"]["max_detections"], cfg["sensitivity_policy"]["max_detections"]):
        run(base + ["eval", "--config", args.config, *extra, "--cap", cap, "--out-dir", results], log)
        path = results / f"eval_{model_key}_cap{cap}.json"
        evals[cap] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "FAIL"}
    return evals


def evaluator_run(model_key, cfg, args, results, log):
    data = Path(cfg["work_root"]) / "smoke" / "data"
    cap = cfg["candidate_policy"]["max_detections"]
    preds = load_json(results / f"predictions_{model_key}_cap{cap}.json")
    ev = cfg["evaluator"]
    full = ReferenceEvaluator(load_json(data / "annotations_eval50.json"), preds, categories=ev["categories"],
                              ignore_policy=ev["ignore_policy"], bounds_policy=ev["bounds_policy"])
    ceiling = full.operating_point()
    ceiling.pop("matches")
    cmd = [sys.executable, "-m", "threshold_transfer.evaluate"]
    roles = ("source_selection", "clear_test", "target_test")
    for role in roles:
        ann = load_json(data / f"annotations_{role}.json")
        role_pred = smoke.restrict_predictions(preds, [i["image_id"] for i in ann["images"]])
        path = results / f"predictions_{model_key}_{role}.json"
        path.write_text(json.dumps(role_pred, allow_nan=False), encoding="utf-8")
        flag = role.replace("_", "-")
        cmd += [f"--{flag}-annotations", data / f"annotations_{role}.json", f"--{flag}-predictions", path]
    policy = {"categories": ev["categories"], "ignore_policy": ev["ignore_policy"], "bounds_policy": ev["bounds_policy"],
              "population_mode": "diagnostic", "test_relationship": "disjoint",
              "roles": {r: {"dataset_id": "coco-val2017", "group_namespace": "coco-val2017-no-verified-groups",
                            "population": f"Claude smoke COCO val2017 role split '{r}' (pipeline proof only; "
                                          "not a condition population)"} for r in roles}}
    policy_path = results / f"evaluator_policy_{model_key}.json"
    policy_path.write_text(json.dumps(policy, indent=1), encoding="utf-8")
    out = results / f"evaluator_{model_key}.json"
    cmd += ["--policy", policy_path, "--target-recall", ev["target_recall"], "--output", out]
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    with open(log, "a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(map(str, cmd)) + "\n")
        f.flush()
        code = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=REPO, env=env).returncode
    result = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    compact = None
    if result is not None:
        compact = {"exit_code": code, "role_status": result["role_validation"]["status"],
                   "g0_status": result["g0_status"], "selection_status": result["selection"]["status"],
                   "selected_threshold": result["selection"]["threshold"],
                   "role_counts": result["role_validation"]["counts"],
                   "ceiling_recall": {r: result["populations"][r]["candidate_ceiling"]["recall"]
                                      for r in result["populations"]},
                   "limitations_count": len(result["role_validation"]["limitations"])}
    return {"evaluator_cli": compact or {"exit_code": code, "status": "FAIL"},
            "full_population_ceiling": ceiling}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/smoke/smoke_config.json")
    p.add_argument("--models", nargs="+", default=None)
    p.add_argument("--ultralytics-python", default=ULTRA)
    p.add_argument("--rtdetrv2-python", default=RTDETR)
    p.add_argument("--skip-train", action="store_true")
    a = p.parse_args(argv)
    cfg = json.loads((REPO / a.config).read_text(encoding="utf-8"))
    results = Path(cfg["work_root"]) / "smoke" / "results"
    results.mkdir(parents=True, exist_ok=True)
    log = results / "run_smoke.log"
    for model_key in a.models or list(cfg["models"]):
        out = {"model": model_key}
        if not a.skip_train:
            out["training"] = train_model(model_key, cfg, a, results, log)
        out["evaluation"] = eval_model(model_key, cfg, a, results, log)
        primary = out["evaluation"][cfg["candidate_policy"]["max_detections"]]
        sens = out["evaluation"][cfg["sensitivity_policy"]["max_detections"]]
        if primary.get("status") == "PASS" and sens.get("status") == "PASS":
            out["cap_censoring"] = smoke.cap_censoring(primary, sens)
            out["evaluator"] = evaluator_run(model_key, cfg, a, results, log)
        if model_key == "yolo26s":
            ipath = results / "inspect_yolo26s.json"
            base, extra = harness(model_key, cfg, a)
            run(base + ["inspect", "--config", a.config, *extra, "--out", ipath], log)
            out["head_inspection"] = json.loads(ipath.read_text(encoding="utf-8")) if ipath.exists() else None
        (results / f"model_{model_key}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        print(model_key, "done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
