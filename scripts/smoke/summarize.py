"""Collect raw smoke results into docs/claude/model_feasibility_smoke.json (Claude).

  python scripts/smoke/summarize.py --config configs/smoke/smoke_config.json \
      --out docs/claude/model_feasibility_smoke.json

Verdict rule per model (mechanical feasibility only): PASS iff the final run completed
the requested optimizer steps at the chosen batch with every loss finite and the
memory fit rule satisfied, both evaluation runs exported valid canonical candidates
for all 50 images, and the reference-evaluator CLI exited 0. Otherwise FAIL, naming the
first failing stage. A PASS is not a performance result and does not pass G0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GIB = 2 ** 30


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verdict(m, cfg):
    tr = m.get("training", {})
    final = tr.get("final")
    if tr.get("chosen_batch") is None:
        return "FAIL", "training: no candidate batch passed the probe"
    if not final or final.get("status") != "PASS" or final.get("optimizer_steps") != cfg["iterations"]:
        return "FAIL", f"training: {final.get('error') if final else 'no final run'}"
    if not final["summary"]["all_losses_finite"] or not final["fits_rule"]:
        return "FAIL", "training: non-finite loss or memory fit rule violated"
    for cap, ev in m["evaluation"].items():
        if ev.get("status") != "PASS":
            return "FAIL", f"evaluation cap {cap}: {ev.get('error')}"
    if m.get("evaluator", {}).get("evaluator_cli", {}).get("exit_code") != 0:
        return "FAIL", "reference evaluator CLI did not exit 0"
    return "PASS", None


def compact_eval(ev):
    keep = ("status", "cap", "score_floor", "memory", "seconds_per_image", "export", "native_postprocessing",
            "end2end_selected", "resolved_predict_args", "fp16_backend", "nms_time_limit_warnings",
            "ultralytics_warnings", "checkpoint_load", "error")
    out = {k: ev[k] for k in keep if k in ev}
    if "per_image" in ev:
        out["per_image"] = {i: {k: s[k] for k in ("native_rows", "kept", "kept_person", "below_floor",
                                                   "removed_by_cap", "cap_binding", "min_kept_score",
                                                   "outside_image_bounds")}
                            for i, s in ev["per_image"].items()}
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/smoke/smoke_config.json")
    p.add_argument("--out", default="docs/claude/model_feasibility_smoke.json")
    a = p.parse_args(argv)
    cfg = load(REPO / a.config)
    work = Path(cfg["work_root"]) / "smoke"
    results = work / "results"
    manifest = load(work / "data" / "selection_manifest.json")
    doc = {"schema": "claude-model-feasibility-smoke-v1", "researcher": "Claude",
           "status_note": "Mechanical RTX 5060 feasibility smoke on COCO val2017 development images. "
                          "Not a performance result. G0 remains PENDING.",
           "g0_status": "PENDING", "config": cfg,
           "config_sha256": hashlib.sha256((REPO / a.config).read_bytes()).hexdigest(),
           "selection": {k: manifest[k] for k in ("rule", "quotas", "strata_counts", "eval_population",
                                                  "selection_seed", "train_seed", "annotation_sha256")},
           "selection_rows": manifest["selection"],
           "train_pool": {k: v for k, v in manifest["train_pool"].items() if k != "image_ids"},
           "train_pool_image_ids": manifest["train_pool"]["image_ids"],
           "evaluator_role_split": manifest["evaluator_role_split"],
           "environment_pins": load(REPO / "configs" / "smoke" / "env" / "env_pins.json"),
           "models": {}}
    for key in cfg["models"]:
        path = results / f"model_{key}.json"
        if not path.exists():
            doc["models"][key] = {"verdict": "NOT_RUN"}
            continue
        m = load(path)
        status, reason = verdict(m, cfg)
        final = m["training"]["final"] or {}
        evals = {str(c): compact_eval(e) for c, e in m["evaluation"].items()}
        primary = m["evaluation"][str(cfg["candidate_policy"]["max_detections"])] \
            if str(cfg["candidate_policy"]["max_detections"]) in m["evaluation"] \
            else m["evaluation"].get(cfg["candidate_policy"]["max_detections"], {})
        doc["models"][key] = {
            "verdict": status, "failure_stage": reason,
            "headline": {
                "chosen_batch": m["training"]["chosen_batch"],
                "optimizer_steps": final.get("optimizer_steps"),
                "scaler_skipped_steps": final.get("scaler_skipped_steps"),
                "all_losses_finite": final.get("summary", {}).get("all_losses_finite"),
                "train_peak_allocated_gib": round(final["memory"]["max_allocated_bytes"] / GIB, 3) if final else None,
                "train_peak_reserved_gib": round(final["memory"]["max_reserved_bytes"] / GIB, 3) if final else None,
                "median_seconds_per_iteration_after_first": final.get("summary", {}).get("median_seconds_after_first"),
                "first_iteration_seconds": final.get("summary", {}).get("first_iteration_seconds"),
                "eval_peak_reserved_gib": round(primary["memory"]["max_reserved_bytes"] / GIB, 3)
                if primary.get("memory") else None,
                "eval_median_seconds_per_image": primary.get("seconds_per_image", {}).get("median_after_first"),
                "candidates_per_image_mean": primary.get("export", {}).get("candidates_per_image_mean"),
                "person_candidates_per_image_mean": primary.get("export", {}).get("person_candidates_per_image_mean"),
                "images_cap_binding": primary.get("export", {}).get("images_cap_binding"),
                "cap_censoring_vs_sensitivity": m.get("cap_censoring"),
            },
            "probes": m["training"]["probes"],
            "final_training": {k: final.get(k) for k in ("status", "requested_batch", "trainer", "recipe", "train_args",
                                                          "overrides", "checkpoint_load", "memory", "summary",
                                                          "iterations", "runtime", "error")},
            "evaluation": evals,
            "evaluator": m.get("evaluator"),
            "head_inspection": m.get("head_inspection"),
        }
    out = REPO / a.out
    out.write_text(json.dumps(doc, indent=1, allow_nan=False, default=str) + "\n", encoding="utf-8")
    for k, v in doc["models"].items():
        print(k, v["verdict"], v.get("failure_stage"), json.dumps(v.get("headline"), default=str)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
