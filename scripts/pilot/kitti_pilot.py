"""Bounded candidate-policy/head/geometry pilot on 32 KITTI development images (Claude).

  python -I scripts/pilot/kitti_pilot.py select    --config configs/research/development_pilot.json
  python -I scripts/pilot/kitti_pilot.py capture   --config ... --pipeline yolo26s_o2o   (GPU; see below)
  python -I scripts/pilot/kitti_pilot.py summarize --config ... --out docs/claude/...json

``select`` (CPU) verifies the KITTI layout, applies the fixed filename-hash rule and records
image sizes; no labels or detector outputs are read. ``capture`` runs ONE native pass per
pipeline at the capture policy plus the native check policies, reconstructs stable primitive
identities (anchor/query + class), per-stage omitted-score bounds, ties, geometry and resource
use, and writes private per-image rows. ``summarize`` (CPU) derives the floor x cap grid from
the captures only where the native check matched, and writes the compact aggregate.

STATUS 2026-11-09: ``capture`` is DISABLED pending the recorded runtime review fixes.
The retained implementation is an unrun prototype, not a usable capture command.
``summarize_capture`` refuses measured-grid approval; prototype arithmetic is tested separately.
The GPU was occupied by an unrelated user
training job and the coordinator stopped the GPU portion. The capture code is unverified at
runtime; the first run must treat any reconstruction mismatch as a bug, not a result.
Ultralytics runs in det-eval-2d/.venv and RT-DETRv2 in ar-work/venv-rtdetrv2 (read-only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from threshold_transfer import candidate_pilot as P  # noqa: E402
from threshold_transfer.data import load_json, write_json  # noqa: E402

GIB = 2 ** 30
CHECK_KEYS = ("identical_identities", "within_tolerance")
_CONSUMED_INPUTS = set()
CAPTURE_HOLD = ("DISABLED: native capture remains on review hold (resource enforcement, identity "
                "replay, checkpoint and cache binding). Coordinate any future GPU window first; "
                "this prototype has no override or automatic start.")


def _require_capture_ready():
    raise SystemExit(CAPTURE_HOLD)


def _load(path):
    _CONSUMED_INPUTS.add(Path(path).resolve())
    return load_json(path)


def _write(obj, path):
    write_json(obj, path, protected_inputs=list(_CONSUMED_INPUTS),
               protected_roots=[REPO / "data"])


def _paths(config):
    cfg = _load(config)
    private = Path(cfg["private_output_dir"])
    out = (REPO / private / "kitti_pilot").resolve()
    if private.is_absolute() or not out.is_relative_to((REPO / "outputs").resolve()):
        raise SystemExit("BLOCKED: private output must remain inside repository outputs/")
    return cfg, cfg["kitti_pilot"], _load(REPO / "configs/smoke/smoke_config.json"), out


# ----------------------------------------------------------------------------- select (CPU)

def cmd_select(cfg, pilot, out):
    from PIL import Image

    image_dir = Path(pilot["image_dir"])
    names = sorted(p.name for p in image_dir.glob("*.png"))
    if len(names) != pilot["expected_png_count"]:
        raise SystemExit(f"expected {pilot['expected_png_count']} PNGs, found {len(names)}")
    chosen = P.select_images(names, seed=pilot["selection_seed"], count=pilot["images"])
    sizes = {}
    for n in names:
        with Image.open(image_dir / n) as im:  # header only
            sizes[n] = im.size
    record = {"image_dir": str(image_dir), "population": len(names),
              "population_sizes": {f"{w}x{h}": c for (w, h), c in Counter(sizes.values()).most_common()},
              "selection_seed": pilot["selection_seed"], "selected": chosen,
              "selected_sizes": {n: list(sizes[n]) for n in chosen}}
    _write(record, out / "selection.json")
    print(json.dumps({k: v for k, v in record.items() if k != "selected_sizes"}, indent=1))


# ------------------------------------------------------------------------ capture (GPU, unrun)

_PROC = re.compile(r"^\|\s+\d+\s+\S+\s+\S+\s+(\d+)\s+(C\+G|C|G)\s+(.+?)\s+\S+\s*\|$")


def compute_processes(table: str) -> list[str]:
    """Compute or ambiguous combined graphics/compute rows; never assume C+G is idle."""
    return [f"{m[1]} {m[3]}" for m in (_PROC.match(line.rstrip()) for line in table.splitlines())
            if m and m[2] in ("C", "C+G")]


def gpu_preflight(limit_reserved_gib):
    """One-shot refusal (no polling): any other compute process on the GPU blocks the run."""
    table = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=True).stdout
    if not isinstance(table, str) or not all(x in table for x in ("Processes:", "GPU", "PID", "Type")):
        raise SystemExit("BLOCKED: unsupported or incomplete GPU process table")
    rows = [_PROC.match(line.rstrip()) for line in table.splitlines()]
    parsed_rows = [row for row in rows if row]
    if not parsed_rows and "No running processes found" not in table:
        raise SystemExit("BLOCKED: GPU occupancy is unknown")
    for line in table.splitlines():
        if re.match(r"^\|\s+\d+\s+\S+\s+\S+\s+\d+\s+", line) and not _PROC.match(line.rstrip()):
            raise SystemExit("BLOCKED: unrecognized GPU process row")
    others = compute_processes(table)
    if others:
        raise SystemExit(f"BLOCKED: GPU has other compute processes {others}; not sharing the GPU")
    return {"other_compute_processes": 0, "reserved_limit_gib": limit_reserved_gib}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _unletterbox(boxes, img_shape, orig_hw):
    """Inverse of Ultralytics LetterBox (same gain/pad as ops.scale_boxes) WITHOUT clipping."""
    h0, w0 = orig_hw
    gain = min(img_shape[0] / h0, img_shape[1] / w0)
    new_h, new_w = max(round(h0 * gain), 1), max(round(w0 * gain), 1)
    gy, gx = new_h / h0, new_w / w0
    px, py = round((img_shape[1] - new_w) / 2 - 0.1), round((img_shape[0] - new_h) / 2 - 0.1)
    return [((b[0] - px) / gx, (b[1] - py) / gy, (b[2] - px) / gx, (b[3] - py) / gy) for b in boxes]


def _ultra_rows(head, captured, result, floor, cap, end2end, names, person):
    """Rows with primitive identity for one Ultralytics predict call (native result + hook)."""
    import torch
    from ultralytics.utils import nms as unms

    y, preds = captured["out"]
    conf = result.boxes.conf.cpu()
    cls = result.boxes.cls.cpu()
    xyxy = result.boxes.xyxy.cpu().tolist()
    stages = {}
    if end2end:
        dec = head._inference(preds["one2one"]).permute(0, 2, 1)
        scores = dec[..., 4:4 + head.nc]
        s, lab, idx = head.get_topk_index(scores, head.max_det)
        if not (torch.equal(s[0, :, 0], y[0, :, 4]) and torch.equal(lab[0, :, 0], y[0, :, 5])):
            raise RuntimeError("O2O top-k reconstruction differs from the head output")
        keep = (s[0, :, 0] > floor).nonzero().view(-1)[:cap]
        ids = [f"a{int(idx[0, k])}:c{int(lab[0, k, 0])}" for k in keep]
        sel_scores, sel_cls = s[0, keep, 0].cpu(), lab[0, keep, 0].cpu()
        letterbox = y[0, keep, :4].tolist()
        full = scores[0].clone()
        full[idx[0], lab[0, :, 0].long()] = float("-inf")
        omitted = float(full.max())
        stages["head_topk"] = {"hidden_k": int(head.max_det), "pool": int(scores[0].numel()),
                               "anchors": int(scores.shape[1]), "bound": omitted, "exact": True,
                               "omitted_count": int(scores[0].numel() - s.shape[1])}
        pool = [{"id": f"a{a}:c{person}", "score": float(v)} for a, v in enumerate(scores[0, :, person].tolist())]
    else:
        out_u, keepi = unms.non_max_suppression(y.clone(), floor, 0.7, None, False, max_det=10 ** 7, nc=0,
                                                end2end=False, return_idxs=True)
        u, ki = out_u[0], keepi[0]
        pre = int((y[0, 4:4 + head.nc].amax(0) > floor).sum())
        sel_scores, sel_cls = u[:cap, 4].cpu(), u[:cap, 5].cpu()
        letterbox = u[:cap, :4].tolist()
        ids = [f"a{int(a)}:c{int(c)}" for a, c in zip(ki[:cap], u[:cap, 5])]
        stages["pre_nms"] = {"candidates_above_floor": pre, "max_nms_overflow": pre > 30000}
        stages["post_nms_cap"] = {"uncapped_nms_rows": int(u.shape[0]),
                                  "bound": float(u[cap, 4]) if u.shape[0] > cap else None, "exact": True,
                                  "omitted_count": max(0, int(u.shape[0]) - cap)}
        pool = [{"id": f"a{int(a)}:c{person}", "score": float(r[4])} for a, r in zip(ki, u) if int(r[5]) == person]
    if not (torch.equal(sel_scores, conf) and torch.equal(sel_cls, cls)):
        raise RuntimeError("identity reconstruction does not match the native predict output")
    stages["floor"] = {"bound": floor, "inclusive": True, "comparator": ">"}
    unclipped = _unletterbox(letterbox, captured["shape"], result.orig_shape)
    rows = [{"id": i, "score": float(sc), "cls": names[int(c)], "box": b, "box_unclipped": list(ub)}
            for i, sc, c, b, ub in zip(ids, conf.tolist(), cls.tolist(), xyxy, unclipped)]
    return rows, pool, stages


def capture_ultralytics(pilot, smoke, key, selection, out):
    _require_capture_ready()
    import torch
    from ultralytics import YOLO
    from ultralytics.utils import LOGGER

    spec = pilot["pipelines"][key]
    m = smoke["models"][spec["model"]]
    record = {"pipeline": key, "status": "FAIL", "comparator": ">", "checkpoint_sha256_verified":
              _sha256(m["weights"]) == m["sha256"]}
    if not record["checkpoint_sha256_verified"]:
        raise SystemExit("checkpoint hash mismatch")
    warnings = []
    LOGGER.addHandler(type("H", (logging.Handler,), {"emit": lambda s, r: warnings.append(r.getMessage())})())
    if spec["model"] == "yolo26s":
        ck = torch.load(m["weights"], map_location="cpu", weights_only=False)
        head0 = (ck.get("ema") or ck["model"]).model[-1]
        record["checkpoint_branches_before_fusion"] = {
            n: (sum(p.numel() for p in head0._modules[n].parameters()) if head0._modules.get(n) is not None else None)
            for n in ("cv2", "cv3", "one2one_cv2", "one2one_cv3")}
        del ck, head0
    floor, cap = pilot["capture_policy"]["score_floor"], pilot["capture_policy"]["max_detections"]
    image_dir = Path(pilot["image_dir"])
    t0 = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    model = YOLO(m["weights"])  # fresh load per pipeline/head
    names = model.names
    person = next(k for k, v in names.items() if v == pilot["person_class"])

    def kwargs(f, c):
        kw = dict(conf=f, iou=pilot["nms_iou"], max_det=c, agnostic_nms=False, imgsz=pilot["imgsz"],
                  device=0, verbose=False, batch=1)
        if spec["nms"] is not None:
            kw["nms"] = spec["nms"]
        return kw

    first = image_dir / selection["selected"][0]
    model.predict(str(first), **kwargs(floor, cap))  # predictor setup (counted in elapsed time)
    pm = model.predictor.model
    head = pm.model.model[-1] if hasattr(pm.model, "model") else pm.model[-1]
    end2end = bool(pm.end2end)
    record["resolved"] = {"backend_end2end": end2end, "nms_arg": spec["nms"],
                          "fused_has_o2m": head._modules.get("cv2") is not None,
                          "fused_has_o2o": head._modules.get("one2one_cv2") is not None,
                          "predict_args": {k: getattr(model.predictor.args, k, None) for k in
                                           ("conf", "iou", "max_det", "agnostic_nms", "nms", "imgsz", "classes")}}
    if end2end != spec["expect_end2end"]:
        record["error"] = "UNSUPPORTED: resolved head differs from the requested head"
        _write(record, out / f"capture_{key}.json")
        return
    captured = {}
    hook = head.register_forward_hook(lambda mod, inp, o: captured.__setitem__("out", o))
    net = pm.model  # the fused DetectionModel; its input is the letterboxed tensor
    pre_hook = net.register_forward_pre_hook(lambda mod, inp: captured.__setitem__("shape", tuple(inp[0].shape[2:])))
    images = []
    try:
        for n in selection["selected"]:
            res = model.predict(str(image_dir / n), **kwargs(floor, cap))[0]
            rows, pool, stages = _ultra_rows(head, captured, res, floor, cap, end2end, names, person)
            h0, w0 = res.orig_shape
            images.append({"file": n, "width": w0, "height": h0, "letterbox_shape": list(captured["shape"]),
                           "rows": rows, "person_pool": pool, "stages": stages})
        record["checks"] = []
        for chk in pilot["native_check_policies"]:
            f, c = chk["score_floor"], chk["max_detections"]
            per = []
            for img in images:
                res = model.predict(str(image_dir / img["file"]), **kwargs(f, c))[0]
                rows, _, _ = _ultra_rows(head, captured, res, f, c, end2end, names, person)
                per.append(P.compare(P.derive(img["rows"], floor=f, cap=c, comparator=">"), rows,
                                     score_tol=0.0, box_tol=1e-3))
            record["checks"].append({"policy": chk, "images": len(per),
                                     **{k: sum(p[k] for p in per) for k in CHECK_KEYS},
                                     "max_abs_score_diff": max(p["max_abs_score_diff"] for p in per),
                                     "max_abs_box_diff": max(p["max_abs_box_diff"] for p in per)})
        record["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001 - recorded, not hidden
        record["error"] = f"{type(exc).__name__}: {exc}"[:2000]
    finally:
        hook.remove()
        pre_hook.remove()
    record.update({"images": images, "elapsed_seconds": time.perf_counter() - t0,
                   "max_reserved_gib": torch.cuda.max_memory_reserved() / GIB,
                   "max_allocated_gib": torch.cuda.max_memory_allocated() / GIB,
                   "nms_time_limit_warnings": sum("time limit" in w for w in warnings),
                   "warnings": sorted(set(warnings))[:20]})
    _write(record, out / f"capture_{key}.json")
    print(key, record["status"], record.get("error", ""))


def capture_rtdetr(pilot, smoke, out, selection):
    _require_capture_ready()
    import torch
    import torchvision.transforms as T
    from PIL import Image

    m = smoke["models"]["rtdetrv2_r18vd"]
    sys.path.insert(0, str(Path(m["repo"])))
    from src.core import YAMLConfig  # RT-DETR repository package
    from src.data.dataset.coco_dataset import mscoco_label2category, mscoco_category2name

    record = {"pipeline": "rtdetrv2_r18vd", "status": "FAIL", "comparator": ">=",
              "checkpoint_sha256_verified": _sha256(m["weights"]) == m["sha256"]}
    floor, cap = pilot["capture_policy"]["score_floor"], pilot["capture_policy"]["max_detections"]
    t0 = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    yc = YAMLConfig(str(Path(m["repo"]) / m["config"]), PResNet={"pretrained": False})
    state = torch.load(m["weights"], map_location="cpu", weights_only=False)
    yc.model.load_state_dict(state["ema"]["module"] if "ema" in state else state["model"], strict=True)
    model, post = yc.model.deploy().cuda(), yc.postprocessor.deploy().cuda()
    transform = T.Compose([T.Resize((pilot["imgsz"], pilot["imgsz"])), T.ToTensor()])
    names = {k: mscoco_category2name[mscoco_label2category[k]] for k in range(80)}
    person = next(k for k, v in names.items() if v == pilot["person_class"])
    image_dir = Path(pilot["image_dir"])

    def run(pil, k):
        w, h = pil.size
        with torch.no_grad():
            outputs = model(transform(pil)[None].cuda())
            post.num_top_queries = k
            labels, boxes, scores = post(outputs, torch.tensor([[w, h]], device="cuda"))
            flat = outputs["pred_logits"].sigmoid().flatten(1)
            s, index = torch.topk(flat, k + 1, dim=-1)
        if not torch.equal(s[0, :k], scores[0]):
            raise RuntimeError("RT-DETR top-k reconstruction differs from the postprocessor")
        ids = [f"q{int(i) // 80}:c{int(i) % 80}" for i in index[0, :k]]
        rows = [{"id": i, "score": float(sc), "cls": names[int(lab)], "box": list(map(float, b))}
                for i, sc, lab, b in zip(ids, scores[0].tolist(), labels[0].tolist(), boxes[0].tolist())]
        pool = [{"id": f"q{q}:c{person}", "score": float(v)}
                for q, v in enumerate(outputs["pred_logits"][0, :, person].sigmoid().tolist())]
        return rows, pool, {"topk": {"pool": int(flat.shape[1]), "bound": float(s[0, k]), "exact": True,
                                     "omitted_count": int(flat.shape[1]) - k},
                            "export_floor": {"bound": floor, "inclusive": False, "comparator": ">="}}

    images = []
    try:
        for n in selection["selected"]:
            pil = Image.open(image_dir / n).convert("RGB")
            rows, pool, stages = run(pil, cap)
            rows = [r for r in rows if P.passes(r["score"], floor, ">=")]
            images.append({"file": n, "width": pil.size[0], "height": pil.size[1], "rows": rows,
                           "person_pool": pool, "stages": stages})
        record["checks"] = []
        for chk in pilot["native_check_policies"]:
            f, c = chk["score_floor"], chk["max_detections"]
            per = []
            for img in images:
                rows, _, _ = run(Image.open(image_dir / img["file"]).convert("RGB"), c)
                rows = [r for r in rows if P.passes(r["score"], f, ">=")]
                per.append(P.compare(P.derive(img["rows"], floor=f, cap=c, comparator=">="), rows, box_tol=1e-3))
            record["checks"].append({"policy": chk, "images": len(per),
                                     **{k: sum(p[k] for p in per) for k in CHECK_KEYS},
                                     "max_abs_score_diff": max(p["max_abs_score_diff"] for p in per),
                                     "max_abs_box_diff": max(p["max_abs_box_diff"] for p in per)})
        record["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"[:2000]
    record.update({"images": images, "elapsed_seconds": time.perf_counter() - t0,
                   "max_reserved_gib": torch.cuda.max_memory_reserved() / GIB,
                   "max_allocated_gib": torch.cuda.max_memory_allocated() / GIB})
    _write(record, out / "capture_rtdetrv2_r18vd.json")
    print("rtdetrv2_r18vd", record["status"], record.get("error", ""))


# --------------------------------------------------------------------------- summarize (CPU)

def _summarize_capture_prototype(cap_record, pilot):
    """Compact per-pipeline aggregate. Derived grid cells are emitted only if every native check
    reproduced the derived identities exactly; otherwise the grid is marked UNSUPPORTED."""
    key = cap_record["pipeline"]
    comparator = cap_record["comparator"]
    images = cap_record.get("images", [])
    checks = cap_record.get("checks", [])
    derivable = (cap_record.get("status") == "PASS" and checks
                 and all(c["identical_identities"] == c["images"] for c in checks))
    out = {"status": cap_record.get("status"), "error": cap_record.get("error"),
           "resolved": cap_record.get("resolved"),
           "checkpoint_branches_before_fusion": cap_record.get("checkpoint_branches_before_fusion"),
           "native_checks": checks, "derivation_supported": bool(derivable),
           "resources": {k: cap_record.get(k) for k in ("elapsed_seconds", "max_reserved_gib",
                                                        "max_allocated_gib", "nms_time_limit_warnings")},
           "image_sizes": dict(Counter(f"{i['width']}x{i['height']}" for i in images))}
    if not derivable:
        out["grid"] = "UNSUPPORTED (no exact native check)"
        return key, out
    grid = {}
    for f in pilot["sensitivity_floors"]:
        for c in pilot["sensitivity_caps"]:
            kept, person, binding, ties, person_class_first, removed_person = [], [], 0, 0, [], 0
            clip, collapsed, outside_native = 0, 0, 0
            for img in images:
                rows = P.derive(img["rows"], floor=f, cap=c, comparator=comparator)
                b = P.boundary(img["rows"], floor=f, cap=c, comparator=comparator)
                kept.append(len(rows))
                np_ = sum(r["cls"] == pilot["person_class"] for r in rows)
                person.append(np_)
                binding += b["cap_binding"]
                ties += b["tie_at_cap_boundary"]
                cf = P.class_first(img["person_pool"], floor=f, cap=c, comparator=comparator)
                person_class_first.append(len(cf))
                full_person = sum(r["cls"] == pilot["person_class"] for r in
                                  P.derive(img["rows"], floor=f, cap=len(img["rows"]) or 1, comparator=comparator))
                removed_person += full_person - np_
                g = P.geometry([r["box"] for r in rows], img["width"], img["height"])
                outside_native += P.geometry([r.get("box_unclipped", r["box"]) for r in rows],
                                             img["width"], img["height"])["changed_by_clip"]
                clip += g["changed_by_clip"]
                collapsed += g["collapsed_after_clip"]
            n = len(images) or 1
            grid[f"floor={f:g},cap={c}"] = {
                "mean_kept": sum(kept) / n, "max_kept": max(kept, default=0),
                "mean_person_all_class_first": sum(person) / n,
                "mean_person_class_first_pipeline": sum(person_class_first) / n,
                "images_cap_binding": binding, "images_tie_at_cap": ties,
                "person_removed_by_cap_vs_capture": removed_person,
                "native_boxes_outside_image_before_native_clip": outside_native,
                "common_clip_changed_boxes": clip, "common_clip_collapsed_boxes": collapsed}
    out["grid"] = grid
    out["capture_stage_bounds"] = {
        name: {"images_with_omissions": sum(1 for i in images if (i["stages"].get(name) or {}).get("omitted_count")),
               "max_omitted_score": max(((i["stages"].get(name) or {}).get("bound") or 0.0) for i in images)}
        for name in sorted({s for i in images for s in i["stages"] if isinstance(i["stages"][s], dict)
                            and "omitted_count" in i["stages"][s]})}
    return key, out


def summarize_capture(cap_record, pilot):
    """Do not approve a measured grid before native identity/resource/binding fixes.

    The private prototype above remains only to reproduce the original synthetic
    arithmetic; a PASS string or matching row counts is not a runtime certificate.
    """
    return cap_record["pipeline"], {
        "status": "UNSUPPORTED_NATIVE_VALIDATION_PENDING",
        "derivation_supported": False,
        "grid": "UNSUPPORTED: native replay, resource and cache binding review fixes pending",
    }


def cmd_summarize(cfg, pilot, out, summary_path):
    selection = _load(out / "selection.json")
    pipelines = {}
    for key in pilot["pipelines"]:
        path = out / f"capture_{key}.json"
        pipelines[key] = summarize_capture(_load(path), pilot)[1] if path.exists() else {
            "status": "BLOCKED", "reason": "capture not run (GPU occupied by an unrelated user job; "
                                           "coordinator stopped the GPU portion)"}
    summary = {"author": "Claude (Opus 5.5), 2026-11-09, base 9794d81; not GPT-reviewed",
               "status": "development pilot; no ACDC/BDD detector output; G0 pending",
               "selection": {k: selection[k] for k in ("population", "population_sizes", "selection_seed")},
               "selected_size_counts": dict(Counter(f"{w}x{h}" for w, h in selection["selected_sizes"].values())),
               "pipelines": pipelines}
    _write(summary, Path(summary_path))
    print(json.dumps({k: v.get("status") for k, v in pipelines.items()}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("mode", choices=("select", "capture", "summarize"))
    p.add_argument("--config", required=True)
    p.add_argument("--pipeline")
    p.add_argument("--out")
    a = p.parse_args(argv)
    if a.mode in ("capture", "summarize"):
        _require_capture_ready()  # before config reads, GPU queries or model imports
    cfg, pilot, smoke, out = _paths(a.config)
    if a.mode == "select":
        return cmd_select(cfg, pilot, out)
    if a.mode == "summarize":
        return cmd_summarize(cfg, pilot, out, a.out)
    gpu_preflight(pilot["max_reserved_gib"])
    selection = _load(out / "selection.json")
    if a.pipeline == "rtdetrv2_r18vd":
        return capture_rtdetr(pilot, smoke, out, selection)
    return capture_ultralytics(pilot, smoke, a.pipeline, selection, out)


if __name__ == "__main__":
    raise SystemExit(main())
