"""Ultralytics YOLO11s / YOLO26s smoke harness (Claude, G0 mechanical feasibility).

Run with the det-eval-2d virtual environment (read-only use; nothing is installed):

  python -I scripts/smoke/ultralytics_smoke.py train   --config C --model yolo11s --batch 16 --iterations 20 --out F
  python -I scripts/smoke/ultralytics_smoke.py eval    --config C --model yolo26s --cap 300 --out-dir D
  python -I scripts/smoke/ultralytics_smoke.py inspect --config C --model yolo26s --out F

``train`` runs the Ultralytics trainer on the 128-image COCO val2017 smoke pool and stops
after exactly N optimizer steps (nbs = batch so accumulate = 1). ``eval`` runs the
unmodified official checkpoint on the 50 selected images with explicit floor/cap and
writes canonical predictions. ``inspect`` records YOLO26 head branches and default mode.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

from threshold_transfer import smoke  # noqa: E402


class StopSmoke(Exception):
    """Raised from a trainer callback once the requested optimizer steps are complete."""


class WarningCounter(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage()[:300])


def _scalar(v):
    try:
        return float(v.detach().float().sum().item()) if hasattr(v, "detach") else float(v)
    except Exception:  # noqa: BLE001
        return float("nan")


def train(cfg, model_key, batch, iterations, out):
    import torch
    from ultralytics import YOLO

    m = cfg["models"][model_key]
    data_yaml = C.data_dir(cfg) / "yolo" / "data.yaml"
    run_dir = Path(cfg["work_root"]) / "smoke" / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(run_dir)
    record = {"model": model_key, "requested_batch": batch, "requested_iterations": iterations,
              "imgsz": cfg["imgsz"], "runtime": C.runtime(torch), "iterations": []}
    state = {"steps": 0, "scales": []}
    timer = C.Timer(torch)

    def on_train_start(tr):
        record["trainer"] = {"batch_size": tr.batch_size, "accumulate": tr.accumulate, "amp": bool(tr.amp),
                             "optimizer": type(tr.optimizer).__name__,
                             "param_groups": len(tr.optimizer.param_groups),
                             "train_images": len(tr.train_loader.dataset), "batches_per_epoch": len(tr.train_loader),
                             "workers": tr.args.workers, "nbs": tr.args.nbs, "lr0": tr.args.lr0,
                             "mosaic": tr.args.mosaic, "end2end": bool(getattr(tr.model, "end2end", False))}
        original = tr.optimizer_step

        def counted_step():
            before = tr.scaler.get_scale() if tr.scaler.is_enabled() else None
            original()
            after = tr.scaler.get_scale() if tr.scaler.is_enabled() else None
            state["steps"] += 1
            state["scales"].append((before, after))

        tr.optimizer_step = counted_step
        torch.cuda.reset_peak_memory_stats()

    def on_batch_start(tr):
        timer.start()

    def on_batch_end(tr):
        seconds = timer.stop()
        if tr.batch_size != batch:
            raise RuntimeError(f"trainer reduced batch {batch} -> {tr.batch_size} (automatic OOM retry)")
        loss = _scalar(tr.loss) if tr.loss is not None else float("nan")
        items = {k: _scalar(v) for k, v in (tr.loss_items or {}).items()} if isinstance(tr.loss_items, dict) \
            else {"loss_items": [float(x) for x in tr.loss_items]} if tr.loss_items is not None else {}
        flat = [loss] + [x for v in items.values() for x in (v if isinstance(v, list) else [v])]
        before, after = state["scales"][-1] if state["scales"] else (None, None)
        record["iterations"].append({
            "step": state["steps"], "seconds": seconds, "loss": loss if math.isfinite(loss) else str(loss),
            "loss_items": {k: (v if C.finite(v) else str(v)) for k, v in items.items()
                           if not isinstance(v, list)},
            "finite": C.finite(loss) and all(C.finite(x) for x in flat),
            "grad_scale_before": before, "grad_scale_after": after,
            "step_skipped_by_scaler": bool(before is not None and after is not None and after < before),
            "max_allocated_bytes": int(torch.cuda.max_memory_allocated())})
        if not record["iterations"][-1]["finite"]:
            raise RuntimeError(f"non-finite loss at step {state['steps']}: {loss}")
        if state["steps"] >= iterations:
            raise StopSmoke()

    epochs = math.ceil(iterations * batch / cfg["train_pool_size"]) + 1
    status = "FAIL"
    try:
        model = YOLO(m["weights"])
        model.add_callback("on_train_start", on_train_start)
        model.add_callback("on_train_batch_start", on_batch_start)
        model.add_callback("on_train_batch_end", on_batch_end)
        record["train_args"] = dict(data=str(data_yaml), epochs=epochs, imgsz=cfg["imgsz"], batch=batch, nbs=batch,
                                    workers=2, optimizer=m["optimizer"], lr0=m["lr0"], amp=True, val=False, close_mosaic=0,
                                    plots=False, save=False, seed=0, deterministic=True, cache=False, device=0,
                                    project=str(run_dir), name=f"{model_key}_b{batch}_i{iterations}",
                                    exist_ok=True, verbose=False)
        model.train(**record["train_args"])
        record["error"] = "trainer finished before the requested steps"
    except StopSmoke:
        status = "PASS"
    except Exception as exc:  # noqa: BLE001 - recorded, not hidden
        record.update(C.failure(exc))
    record["optimizer_steps"] = state["steps"]
    record["memory"] = C.cuda_memory(torch)
    record["summary"] = C.iteration_summary(record["iterations"])
    record["scaler_skipped_steps"] = sum(r["step_skipped_by_scaler"] for r in record["iterations"])
    fits = (status == "PASS" and record["summary"]["all_losses_finite"]
            and record["memory"]["max_reserved_bytes"] <= cfg["fit_reserved_limit_bytes"])
    record["status"] = status
    record["fits_rule"] = bool(fits)
    C.write_json(record, out)
    print(f"{model_key} batch={batch} status={status} fits={fits} steps={state['steps']} "
          f"reserved={record['memory']['max_reserved_bytes'] / 2**30:.2f}GiB")
    return 0


def _native_policy(model_key, m, cap, floor, end2end):
    if end2end:
        return {"head": "one-to-one (NMS-free)", "predict_nms_arg": False,
                "selection": f"Detect.postprocess top-k over flattened anchor x class scores with "
                             f"k = max(max_det, 300) = {max(cap, 300)}; then conf > floor and [:max_det]",
                "multilabel": "an anchor can appear once per class in the top-k",
                "box_clipping": "scale_boxes clips xyxy to the original image", "nms": None}
    return {"head": "one-to-many (dense) + NMS", "predict_nms_arg": m.get("nms"),
            "selection": "conf > floor on max class score; class-aware torchvision hard NMS; "
                         f"iou={m['iou']}; max_nms=30000 pre-NMS; max_det={cap}",
            "multilabel": "single label per box (predict path multi_label=False)",
            "nms_time_limit": "2.0 + 0.05*batch seconds; on overrun Ultralytics logs a warning and stops",
            "box_clipping": "scale_boxes clips xyxy to the original image"}


def evaluate(cfg, model_key, cap, out_dir):
    import torch
    from ultralytics import YOLO
    from ultralytics.utils import LOGGER

    m = cfg["models"][model_key]
    floor = cfg["candidate_policy"]["score_floor"]
    ann = smoke_load(C.data_dir(cfg) / "annotations_eval50.json")
    img_dir = Path(cfg["det_eval_root"]) / cfg["coco_images"]
    counter = WarningCounter()
    LOGGER.addHandler(counter)
    out_dir = Path(out_dir)
    record = {"model": model_key, "cap": cap, "score_floor": floor, "runtime": C.runtime(torch)}
    try:
        model = YOLO(m["weights"])
        coco_names = sorted(ann["provenance"]["categories"])
        names = model.names
        if sorted(names.values()) != coco_names:
            raise RuntimeError("model class names differ from COCO category names; explicit mapping needed")
        kwargs = dict(conf=floor, iou=m["iou"], max_det=cap, agnostic_nms=m["agnostic_nms"], imgsz=cfg["imgsz"],
                      device=0, verbose=False, batch=1)
        if m.get("nms") is not None:
            kwargs["nms"] = m["nms"]
        record["predict_args"] = dict(kwargs)
        timer = C.Timer(torch)
        rows, sizes, times = {}, {}, []
        torch.cuda.reset_peak_memory_stats()
        for img in ann["images"]:
            path = img_dir / img["file_name"]
            timer.start()
            result = model.predict(str(path), **kwargs)[0]
            times.append(timer.stop())
            boxes = result.boxes
            xyxy = boxes.xyxy.cpu().tolist()
            conf = boxes.conf.cpu().tolist()
            cls = boxes.cls.cpu().tolist()
            h, w = result.orig_shape
            if (w, h) != (img["width"], img["height"]):
                raise RuntimeError(f"{img['image_id']}: decoded size {(w, h)} differs from annotation")
            sizes[img["image_id"]] = (w, h)
            rows[img["image_id"]] = [(*b, s, names[int(c)]) for b, s, c in zip(xyxy, conf, cls)]
        pm = model.predictor.model
        end2end = bool(pm.end2end)
        pa = model.predictor.args
        record["resolved_predict_args"] = {k: getattr(pa, k, None) for k in
                                           ("conf", "iou", "max_det", "agnostic_nms", "nms", "quantize", "imgsz",
                                            "classes", "augment", "batch")}
        record["fp16_backend"] = bool(getattr(pm, "fp16", False))
        record["memory"] = C.cuda_memory(torch)
        record["seconds_per_image"] = {"first": times[0], "median_after_first": sorted(times[1:])[len(times[1:]) // 2],
                                       "total": sum(times)}
        pipeline = {"model_id": f"{model_key}-coco-official", "checkpoint_sha256": m["sha256"],
                    "preprocessing": f"Ultralytics predictor LetterBox new_shape={cfg['imgsz']}, auto=True for a "
                                     "single PyTorch image (long side 640, minimal stride-32 padding), BGR->RGB, "
                                     "/255; boxes scaled back to original pixels",
                    "precision": "fp32", "category_mapping": {}, "candidate_policy":
                        {"score_floor": floor, "max_detections": cap},
                    "native_postprocessing": _native_policy(model_key, m, cap, floor, end2end),
                    "framework": "ultralytics 8.4.197"}
        doc, summary = smoke.export_candidates(rows, model_key=model_key,
                                               evaluated_image_ids=[i["image_id"] for i in ann["images"]],
                                               image_sizes=sizes, score_floor=floor, max_detections=cap,
                                               degenerate_policy="drop_and_count", inference_pipeline=pipeline)
        smoke.validate_pair(ann, doc)
        C.write_json(doc, out_dir / f"predictions_{model_key}_cap{cap}.json")
        record["end2end_selected"] = end2end
        record["native_postprocessing"] = pipeline["native_postprocessing"]
        record["export"] = {k: v for k, v in summary.items() if k != "per_image"}
        record["per_image"] = summary["per_image"]
        record["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001
        record.update(C.failure(exc))
        record["status"] = "FAIL"
    record["ultralytics_warnings"] = sorted(set(counter.messages))
    record["nms_time_limit_warnings"] = sum("time limit" in w for w in counter.messages)
    C.write_json(record, out_dir / f"eval_{model_key}_cap{cap}.json")
    print(f"{model_key} eval cap={cap} status={record['status']}")
    return 0


def inspect(cfg, model_key, out):
    """Record head branches in the checkpoint and which branch each predict setting selects."""
    import torch
    from ultralytics import YOLO

    m = cfg["models"][model_key]
    ck = torch.load(m["weights"], map_location="cpu", weights_only=False)
    net = ck.get("ema") or ck["model"]
    head = net.model[-1]
    branches = {}
    for name in ("cv2", "cv3", "one2one_cv2", "one2one_cv3"):
        module = head._modules.get(name)
        branches[name] = None if module is None else sum(p.numel() for p in module.parameters())
    record = {"model": model_key, "checkpoint_keys": sorted(ck), "ultralytics_version_in_checkpoint": ck.get("version"),
              "train_args_end2end": ck.get("train_args", {}).get("end2end"), "yaml_end2end": net.yaml.get("end2end"),
              "head_type": type(head).__name__, "head_branch_parameters": branches,
              "head_end2end_after_load": bool(head.end2end), "modes": {}}
    first = smoke_load(C.data_dir(cfg) / "annotations_eval50.json")["images"][0]
    path = Path(cfg["det_eval_root"]) / cfg["coco_images"] / first["file_name"]
    for label, nms in (("nms_unset_default", None), ("nms_false", False), ("nms_true", True)):
        model = YOLO(m["weights"])  # separately loaded copy for every mode
        kwargs = dict(conf=cfg["candidate_policy"]["score_floor"], max_det=300, device=0, verbose=False)
        if nms is not None:
            kwargs["nms"] = nms
        result = model.predict(str(path), **kwargs)[0]
        fused = model.predictor.model.model.model[-1]
        record["modes"][label] = {"backend_end2end": bool(model.predictor.model.end2end),
                                  "fused_head_has_o2m": fused._modules.get("cv2") is not None,
                                  "fused_head_has_o2o": fused._modules.get("one2one_cv2") is not None,
                                  "candidates_on_probe_image": len(result.boxes), "probe_image": first["image_id"]}
    C.write_json(record, out)
    print(record)
    return 0


def smoke_load(path):
    from threshold_transfer.schema import load_json
    return load_json(path)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("train", "eval", "inspect"))
    p.add_argument("--config", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--batch", type=int)
    p.add_argument("--iterations", type=int)
    p.add_argument("--cap", type=int)
    p.add_argument("--out")
    p.add_argument("--out-dir")
    a = p.parse_args(argv)
    cfg = C.load_config(a.config)
    if a.mode == "train":
        return train(cfg, a.model, a.batch, a.iterations, a.out)
    if a.mode == "eval":
        return evaluate(cfg, a.model, a.cap, a.out_dir)
    return inspect(cfg, a.model, a.out)


if __name__ == "__main__":
    raise SystemExit(main())
