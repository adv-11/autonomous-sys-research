"""RT-DETRv2-S (R18-vd) smoke harness (Claude, G0 mechanical feasibility).

Run with the separate pinned venv (C:/Users/Advait/ar-work/venv-rtdetrv2):

  python -I scripts/smoke/rtdetrv2_smoke.py train --config C --batch 16 --iterations 20 --out F
  python -I scripts/smoke/rtdetrv2_smoke.py eval  --config C --cap 300 --out-dir D

Uses lyuwenyu/RT-DETR ``rtdetrv2_pytorch`` at the pinned commit with its own
``rtdetrv2_r18vd_120e_coco.yml``. The training loop mirrors that repository's
``src/solver/det_engine.py::train_one_epoch`` (AMP autocast for the model, criterion
outside autocast, GradScaler, clip_max_norm, EMA, linear warmup), adding per-iteration
timing, finiteness checks and an exact step count. Overrides: dataset paths, batch
size, num_workers, and ``PResNet.pretrained=False`` (the full COCO checkpoint is
loaded instead of downloading ImageNet backbone weights).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

from threshold_transfer import smoke  # noqa: E402
from threshold_transfer.schema import load_json  # noqa: E402


def _config(cfg, batch, train_json, eval_json):
    m = cfg["models"]["rtdetrv2_r18vd"]
    repo = Path(m["repo"])
    sys.path.insert(0, str(repo))
    from src.core import YAMLConfig  # noqa: E402  (RT-DETR repository package)

    img_dir = str(Path(cfg["det_eval_root"]) / cfg["coco_images"])
    overrides = {
        "PResNet": {"pretrained": False},
        "device": "cuda",
        "output_dir": str(Path(cfg["work_root"]) / "smoke" / "runs" / "rtdetrv2"),
        "train_dataloader": {"dataset": {"img_folder": img_dir, "ann_file": str(train_json)},
                             "total_batch_size": batch, "num_workers": 2},
        "val_dataloader": {"dataset": {"img_folder": img_dir, "ann_file": str(eval_json)},
                           "total_batch_size": 1, "num_workers": 0},
    }
    return YAMLConfig(str(repo / m["config"]), **overrides), overrides


def _load_checkpoint(cfg, model):
    import torch

    m = cfg["models"]["rtdetrv2_r18vd"]
    state = torch.load(m["weights"], map_location="cpu", weights_only=False)
    source = state["ema"]["module"] if "ema" in state else state["model"]
    own = model.state_dict()
    missed = [k for k in own if k not in source]
    unmatched = [k for k in own if k in source and own[k].shape != source[k].shape]
    unexpected = [k for k in source if k not in own]
    model.load_state_dict({k: v for k, v in source.items() if k in own and own[k].shape == v.shape}, strict=False)
    return {"weights_key": "ema.module" if "ema" in state else "model", "missed": missed,
            "unmatched": unmatched, "unexpected": unexpected}


def train(cfg, batch, iterations, out):
    import torch

    d = C.data_dir(cfg)
    record = {"model": "rtdetrv2_r18vd", "requested_batch": batch, "requested_iterations": iterations,
              "imgsz": cfg["imgsz"], "runtime": C.runtime(torch), "iterations": []}
    status = "FAIL"
    steps = 0
    try:
        yc, overrides = _config(cfg, batch, d / "coco_train128.json", d / "coco_eval50.json")
        record["overrides"] = overrides
        device = torch.device("cuda")
        model = yc.model
        record["checkpoint_load"] = _load_checkpoint(cfg, model)
        if record["checkpoint_load"]["missed"] or record["checkpoint_load"]["unmatched"]:
            raise RuntimeError("checkpoint does not fully match the configured model")
        model = model.to(device)
        criterion = yc.criterion.to(device)
        optimizer = yc.optimizer
        scaler = yc.scaler
        ema = yc.ema.to(device) if yc.ema is not None else None  # built after loading, as the repo requires
        warmup = yc.lr_warmup_scheduler
        loader = yc.train_dataloader
        loader.set_epoch(0)
        max_norm = yc.yaml_cfg.get("clip_max_norm", 0)
        gcfg = yc.yaml_cfg
        record["recipe"] = {"use_amp": bool(gcfg.get("use_amp")), "use_ema": bool(gcfg.get("use_ema")),
                            "clip_max_norm": max_norm, "optimizer": type(optimizer).__name__,
                            "param_group_lrs": [g["lr"] for g in optimizer.param_groups],
                            "collate_scales": gcfg["train_dataloader"]["collate_fn"].get("scales"),
                            "train_images": len(loader.dataset), "batches_per_epoch": len(loader),
                            "drop_last": loader.drop_last, "num_workers": loader.num_workers,
                            "transforms": [op.get("type") for op in gcfg["train_dataloader"]["dataset"]
                                           ["transforms"]["ops"]]}
        model.train()
        criterion.train()
        timer = C.Timer(torch)
        torch.cuda.reset_peak_memory_stats()
        epoch = 0
        while steps < iterations:
            loader.set_epoch(epoch)
            for i, (samples, targets) in enumerate(loader):
                timer.start()
                samples = samples.to(device)
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                metas = dict(epoch=epoch, step=i, global_step=steps)
                with torch.autocast(device_type="cuda", cache_enabled=True, enabled=scaler is not None):
                    outputs = model(samples, targets=targets)
                with torch.autocast(device_type="cuda", enabled=False):
                    loss_dict = criterion(outputs, targets, **metas)
                loss = sum(loss_dict.values())
                values = {k: float(v.detach().item()) for k, v in loss_dict.items()}
                total = float(loss.detach().item())
                before = scaler.get_scale() if scaler is not None else None
                grad_norm = float("nan")
                if scaler is not None:
                    scaler.scale(loss).backward()
                    if max_norm > 0:
                        scaler.unscale_(optimizer)
                        grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm))
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)) \
                        if max_norm > 0 else float("nan")
                    optimizer.step()
                optimizer.zero_grad()
                if ema is not None:
                    ema.update(model)
                if warmup is not None:
                    warmup.step()
                seconds = timer.stop()
                after = scaler.get_scale() if scaler is not None else None
                steps += 1
                fin = C.finite(total) and all(C.finite(v) for v in values.values())
                record["iterations"].append({
                    "step": steps, "seconds": seconds, "loss": total if C.finite(total) else str(total),
                    "loss_terms": len(values), "finite": fin,
                    "grad_norm_before_clip": grad_norm if C.finite(grad_norm) else str(grad_norm),
                    "grad_scale_before": before, "grad_scale_after": after,
                    "step_skipped_by_scaler": bool(before is not None and after < before),
                    "empty_target_images": sum(int(t["labels"].numel() == 0) for t in targets),
                    "input_shape": list(samples.shape),
                    "max_allocated_bytes": int(torch.cuda.max_memory_allocated())})
                if not fin:
                    raise RuntimeError(f"non-finite loss at step {steps}: {total}")
                if steps >= iterations:
                    break
            epoch += 1
        status = "PASS"
    except Exception as exc:  # noqa: BLE001
        record.update(C.failure(exc))
    record["optimizer_steps"] = steps
    record["memory"] = C.cuda_memory(torch)
    record["summary"] = C.iteration_summary(record["iterations"])
    record["scaler_skipped_steps"] = sum(r["step_skipped_by_scaler"] for r in record["iterations"])
    record["status"] = status
    record["fits_rule"] = bool(status == "PASS" and record["summary"]["all_losses_finite"]
                               and record["memory"]["max_reserved_bytes"] <= cfg["fit_reserved_limit_bytes"])
    C.write_json(record, out)
    print(f"rtdetrv2 batch={batch} status={status} fits={record['fits_rule']} steps={steps} "
          f"reserved={record['memory']['max_reserved_bytes'] / 2**30:.2f}GiB")
    return 0


def evaluate(cfg, cap, out_dir):
    import torch
    import torchvision.transforms as T
    from PIL import Image

    d = C.data_dir(cfg)
    m = cfg["models"]["rtdetrv2_r18vd"]
    floor = cfg["candidate_policy"]["score_floor"]
    ann = load_json(d / "annotations_eval50.json")
    coco = load_json(d / "coco_eval50.json")
    id2name = {c["id"]: c["name"] for c in coco["categories"]}
    img_dir = Path(cfg["det_eval_root"]) / cfg["coco_images"]
    out_dir = Path(out_dir)
    record = {"model": "rtdetrv2_r18vd", "cap": cap, "score_floor": floor, "runtime": C.runtime(torch)}
    try:
        yc, overrides = _config(cfg, 1, d / "coco_train128.json", d / "coco_eval50.json")
        from src.data.dataset.coco_dataset import mscoco_label2category  # noqa: E402

        model = yc.model
        record["checkpoint_load"] = _load_checkpoint(cfg, model)
        if record["checkpoint_load"]["missed"] or record["checkpoint_load"]["unmatched"]:
            raise RuntimeError("checkpoint does not fully match the configured model")
        post = yc.postprocessor
        native_k = post.num_top_queries
        post.num_top_queries = cap  # explicit; 300 is the config value
        model = model.deploy().cuda()
        post = post.deploy().cuda()
        transform = T.Compose([T.Resize((cfg["imgsz"], cfg["imgsz"])), T.ToTensor()])
        timer = C.Timer(torch)
        rows, sizes, times = {}, {}, []
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            for img in ann["images"]:
                pil = Image.open(img_dir / img["file_name"]).convert("RGB")
                w, h = pil.size
                if (w, h) != (img["width"], img["height"]):
                    raise RuntimeError(f"{img['image_id']}: decoded size differs from annotation")
                timer.start()
                x = transform(pil)[None].cuda()
                labels, boxes, scores = post(model(x), torch.tensor([[w, h]], device="cuda"))
                times.append(timer.stop())
                labels, boxes, scores = labels[0].tolist(), boxes[0].tolist(), scores[0].tolist()
                sizes[img["image_id"]] = (w, h)
                rows[img["image_id"]] = [(*b, s, id2name[mscoco_label2category[int(lab)]])
                                         for b, s, lab in zip(boxes, scores, labels)]
        native = {"head": "DETR decoder, 300 queries, sigmoid focal (varifocal-trained) class scores",
                  "selection": f"RTDETRPostProcessor top-k over flattened query x class sigmoid scores; "
                               f"config num_top_queries={native_k}, set explicitly to {cap}; no NMS; "
                               "no score threshold; then export floor score >= floor",
                  "multilabel": "a query can appear once per class in the top-k",
                  "box_clipping": "none (cxcywh * original size; boxes may extend outside the image)",
                  "label_mapping": "contiguous label -> mscoco_label2category -> COCO category name"}
        pipeline = {"model_id": "rtdetrv2_r18vd_120e_coco_rerun_48.1", "checkpoint_sha256": m["sha256"],
                    "preprocessing": f"PIL RGB, torchvision Resize(({cfg['imgsz']},{cfg['imgsz']})) without "
                                     "aspect preservation, ToTensor (/255, no mean/std); boxes scaled by original w,h",
                    "precision": "fp32", "category_mapping": {}, "candidate_policy":
                        {"score_floor": floor, "max_detections": cap},
                    "native_postprocessing": native,
                    "framework": f"lyuwenyu/RT-DETR rtdetrv2_pytorch@{m['repo_commit']}",
                    "config": m["config"], "weights_key": record["checkpoint_load"]["weights_key"]}
        doc, summary = smoke.export_candidates(rows, model_key="rtdetrv2_r18vd",
                                               evaluated_image_ids=[i["image_id"] for i in ann["images"]],
                                               image_sizes=sizes, score_floor=floor, max_detections=cap,
                                               degenerate_policy="drop_and_count", inference_pipeline=pipeline)
        smoke.validate_pair(ann, doc)
        C.write_json(doc, out_dir / f"predictions_rtdetrv2_r18vd_cap{cap}.json")
        record["memory"] = C.cuda_memory(torch)
        record["seconds_per_image"] = {"first": times[0], "median_after_first": sorted(times[1:])[len(times[1:]) // 2],
                                       "total": sum(times)}
        record["native_postprocessing"] = native
        record["export"] = {k: v for k, v in summary.items() if k != "per_image"}
        record["per_image"] = summary["per_image"]
        record["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001
        record.update(C.failure(exc))
        record["status"] = "FAIL"
    C.write_json(record, out_dir / f"eval_rtdetrv2_r18vd_cap{cap}.json")
    print(f"rtdetrv2 eval cap={cap} status={record['status']}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("train", "eval"))
    p.add_argument("--config", required=True)
    p.add_argument("--batch", type=int)
    p.add_argument("--iterations", type=int)
    p.add_argument("--cap", type=int)
    p.add_argument("--out")
    p.add_argument("--out-dir")
    a = p.parse_args(argv)
    cfg = C.load_config(a.config)
    if a.mode == "train":
        return train(cfg, a.batch, a.iterations, a.out)
    return evaluate(cfg, a.cap, a.out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
