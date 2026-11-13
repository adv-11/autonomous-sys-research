"""GPT Sol: three fresh common-canvas arms; frozen packet, native post-NMS.

CPU-only aggregation imports the unchanged reference evaluator through the pilot.
Remote inference alone imports torch/Ultralytics. Private boxes/IDs stay ignored.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import inspect
import logging
import math
from pathlib import Path
import time
import traceback

SPEC = importlib.util.spec_from_file_location(
    "pilot", Path(__file__).with_name("2026-11-10_transfer_pilot.py"))
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
ARMS = ("H1280", "L640", "U1280")


def geometry(image):
    w0, h0 = image["width"], image["height"]
    r = 1280 / max(w0, h0)
    w, h = math.floor(r*w0 + .5), math.floor(r*h0 + .5)
    return w, h, (1280-w)//2, (1280-h)//2


def map_gt(manifest):
    """Map each unique annotation once, sharing it across panel memberships."""
    mapped = copy.deepcopy(manifest)
    images = {i["image_id"]: i for p in manifest["panels"].values() for i in p["images"]}
    annotations = {}
    for panel in mapped["panels"].values():
        for a in panel["annotations"]:
            key = a["annotation_id"]
            if key not in annotations:
                i = images[a["image_id"]]
                w, h, left, top = geometry(i)
                x, y, bw, bh = a["bbox"]
                x1, y1 = left+x*w/i["width"], top+y*h/i["height"]
                x2, y2 = left+(x+bw)*w/i["width"], top+(y+bh)*h/i["height"]
                annotations[key] = [x1, y1, x2-x1, y2-y1]
            a["bbox"] = annotations[key]
        for i in panel["images"]:
            i["width"] = i["height"] = 1280
    return mapped


def infer(root):
    pilot.require_colab()
    import torch
    import torch.nn.functional as F
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.utils import LOGGER, patches
    from ultralytics.models.yolo.detect import predict as predict_module
    from ultralytics.utils import nms as nms_module
    root = Path(root)
    result = root / "results"
    result.mkdir(exist_ok=True)
    config, manifest = pilot.read(root/"config.json"), pilot.read(root/"manifest.json")
    status = dict(status="RUNNING", coverage={}, actual_inputs={}, events=[], started=time.time())
    states = {a: dict(predictions=[], degenerate_predictions=[],
                     provenance=dict(evaluated_image_ids=[]), measurements=[]) for a in ARMS}
    events = status["events"]

    class NativeEvents(logging.Handler):
        def emit(self, record):
            msg = record.getMessage()
            if "time limit" in msg.lower() or "nan" in msg.lower():
                events.append(dict(arm=active[0], message=msg))

    active = [None]
    LOGGER.addHandler(NativeEvents())
    try:
        assert ultralytics.__version__ == config["ultralytics"]
        assert torch.__version__ == config["torch"]
        assert pilot.sha(root/"manifest.json") == config["manifest_sha256"]
        assert pilot.sha(root/"yolo11s.pt") == config["models"]["yolo11s"]["sha256"]
        status.update(torch=torch.__version__, ultralytics=ultralytics.__version__,
            checkpoint_sha256=pilot.sha(root/"yolo11s.pt"), device=torch.cuda.get_device_name(0),
            decoder="ultralytics.utils.patches.imread (retained OpenCV decoder)",
            torch_threads=4, config_sha256=pilot.sha(root/"config.json"),
            script_sha256=pilot.sha(Path(__file__)), manifest_sha256=pilot.sha(root/"manifest.json"))
        assert "L4" in status["device"]
        torch.set_num_threads(4)
        for name, module in (("predict", predict_module), ("nms", nms_module), ("decoder", patches)):
            (result/(name+"_source.py")).write_text(inspect.getsource(module), encoding="utf-8")
        model = YOLO(str(root/"yolo11s.pt"))
        calls = []
        def capture(module, args):
            if active[0] not in status["actual_inputs"]:
                calls.append(dict(shape=list(args[0].shape), dtype=str(args[0].dtype)))
        model.model.register_forward_pre_hook(capture)
        images = list({i["image_id"]: i for p in manifest["panels"].values() for i in p["images"]}.values())
        assert len(images) == 700
        mapped = map_gt(manifest)
        first_panel = next(p for p in manifest["panels"].values() if p["annotations"])
        example = first_panel["annotations"][0]
        mapped_example = next(a for p in mapped["panels"].values() for a in p["annotations"]
                              if a["annotation_id"] == example["annotation_id"])
        pilot.write(result/"gt_map_example_private.json", dict(original=example, mapped=mapped_example,
            image=next(i for i in images if i["image_id"] == example["image_id"])))
        hashes = {a: hashlib.sha256() for a in ARMS}
        costs = {a: dict(preprocess_seconds=0., pipeline_seconds=0.) for a in ARMS}
        torch.cuda.reset_peak_memory_stats()
        begun = time.monotonic()
        for start in range(0, len(images), 8):
            batch = images[start:start+8]
            t = time.monotonic()
            hs = []
            for i in batch:
                path = root/i["file_name"]
                bgr = patches.imread(str(path))
                assert bgr.shape == (i["height"], i["width"], 3)
                x = torch.from_numpy(bgr[..., ::-1].copy()).permute(2, 0, 1).to(torch.float32).div_(255).unsqueeze(0)
                w, h, left, top = geometry(i)
                x = F.interpolate(x, size=(h, w), mode="bilinear", align_corners=False, antialias=True)
                hs.append(F.pad(x, (left, 1280-w-left, top, 1280-h-top), value=114/255))
            H = torch.cat(hs).contiguous()
            costs["H1280"]["preprocess_seconds"] += time.monotonic()-t
            t = time.monotonic()
            L = F.interpolate(H, size=(640, 640), mode="bilinear", align_corners=False, antialias=True).contiguous()
            costs["L640"]["preprocess_seconds"] += time.monotonic()-t
            t = time.monotonic()
            U = F.interpolate(L, size=(1280, 1280), mode="bilinear", align_corners=False, antialias=False).contiguous()
            costs["U1280"]["preprocess_seconds"] += time.monotonic()-t
            for arm, tensor in zip(ARMS, (H, L, U)):
                active[0] = arm
                hashes[arm].update(tensor.numpy().tobytes())
                size = tensor.shape[-1]
                t = time.monotonic()
                outputs = list(model.predict(tensor, conf=.0001, max_det=3000, imgsz=size,
                    device=0, half=False, rect=False, batch=8, classes=[0], iou=.70,
                    agnostic_nms=False, augment=False, verbose=False, save=False, stream=True))
                costs[arm]["pipeline_seconds"] += time.monotonic()-t
                # Save native outputs before geometry, event or coverage validation.
                native = [dict(image_id=batch[j]["image_id"] if j < len(batch) else None,
                    xyxy=o.boxes.xyxy.detach().cpu().tolist(), scores=o.boxes.conf.detach().cpu().tolist(),
                    classes=o.boxes.cls.detach().cpu().tolist(), speed=o.speed) for j, o in enumerate(outputs)]
                (result/f"{arm}_native_batch_{start:04d}.json").write_text(
                    pilot.json.dumps(native, allow_nan=True), encoding="utf-8")
                if arm not in status["actual_inputs"]:
                    assert calls and calls[-1] == dict(shape=[len(batch), 3, size, size], dtype="torch.float32")
                    status["actual_inputs"][arm] = calls[-1]
                    calls.clear()
                assert not any("message" in e for e in events), "native time-limit/nonfinite event"
                assert len(outputs) == len(batch)
                state = states[arm]
                for i, o, raw in zip(batch, outputs, native):
                    assert tuple(o.orig_shape) == (size, size)
                    assert len(raw["xyxy"]) == len(raw["scores"]) == len(raw["classes"])
                    if len(raw["xyxy"]) == 3000:
                        events.append(dict(arm=arm, kind="cap3000", image_id=i["image_id"]))
                    for j, (box, score, cls) in enumerate(zip(raw["xyxy"], raw["scores"], raw["classes"])):
                        assert cls == 0 and all(math.isfinite(v) for v in box+[score]) and 0 <= score <= 1
                        x1, y1, x2, y2 = box
                        assert x2 >= x1 and y2 >= y1, "reversed native output"
                        # Native tensor postprocessing already clips to its full canvas;
                        # explicit same-canvas clamp is idempotent. No unpadding/rounding.
                        box = [min(size, max(0., v)) for v in box]
                        if arm == "L640":
                            box = [v*2 for v in box]
                        x1, y1, x2, y2 = box
                        pred = dict(candidate_id=i["image_id"]+f":{j:04d}", image_id=i["image_id"],
                            category="human", bbox=[x1, y1, x2-x1, y2-y1], score=score)
                        if x2 == x1 or y2 == y1:
                            state["degenerate_predictions"].append(dict(**pred, native_xyxy=box))
                        else:
                            state["predictions"].append(pred)
                    state["provenance"]["evaluated_image_ids"].append(i["image_id"])
                    state["measurements"].append(dict(image_id=i["image_id"], candidate_count=len(raw["xyxy"]), speed=o.speed))
                status["coverage"][arm] = len(state["provenance"]["evaluated_image_ids"])
            pilot.write(result/"status.json", status)
            if start % 128 == 0:
                print(pilot.json.dumps(dict(complete=start+len(batch), total=700)), flush=True)
        for arm, state in states.items():
            ids = state["provenance"]["evaluated_image_ids"]
            assert len(ids) == len(set(ids)) == 700
            pilot.write(result/(arm+".json"), state)
        status.update(status="COMPLETE", input_tensor_stream_sha256={a:h.hexdigest() for a,h in hashes.items()},
            costs=costs, loop_seconds=time.monotonic()-begun,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            effective_runtime=dict(end2end=model.predictor.model.end2end, args=vars(model.predictor.args)))
    except BaseException as exc:
        status.update(status="ERROR", error=repr(exc), traceback=traceback.format_exc())
        for arm, state in states.items():
            pilot.write(result/(arm+"_partial.json"), state)
        raise
    finally:
        status["ended"] = time.time()
        pilot.write(result/"status.json", status)


def public_runtime_status(status):
    """Keep event totals, never private image identities or raw messages."""
    result = copy.deepcopy(status)
    events = result.pop("events", [])
    result["cap3000_events_by_arm"] = {
        arm: sum(e.get("kind") == "cap3000" and e.get("arm") == arm for e in events)
        for arm in ARMS
    }
    result["native_time_limit_events"] = sum("message" in e for e in events)
    effective = result.get("effective_runtime", {})
    if "args" in effective:
        allowed = ("conf", "max_det", "imgsz", "rect", "batch", "classes", "iou",
                   "agnostic_nms", "augment", "device")
        effective["args"] = {key: effective["args"][key] for key in allowed if key in effective["args"]}
    return result


def aggregate(root, output):
    root = Path(root)
    status = pilot.read(root/"results/status.json")
    assert status["status"] == "COMPLETE"
    assert pilot.read(root/"results/process_status.json")["returncode"] == 0
    code = pilot.read(root/"code_record.json")
    assert pilot.read(root/"results/delivery_verified.json") == code
    for name, key in (("sent_script.py", "script_sha256"), ("sent_baseline.py", "baseline_script_sha256"),
                      ("packet/config.json", "config_sha256"), ("packet/manifest.json", "manifest_sha256")):
        assert pilot.sha(root/name) == code[key]
    # The delivered historical scripts were checked above; aggregation may add
    # later publication safeguards without pretending those ran on the GPU.
    manifest = map_gt(pilot.read(root/"packet/manifest.json"))
    panels = dict(manifest["panels"])
    for name, members in (("pooled_adverse", ["fog", "night", "rain", "snow"]),
                          ("pooled_normal", [c+"_normal" for c in ("fog", "night", "rain", "snow")]),
                          ("pooled_paired", [c+"_paired" for c in ("fog", "night", "rain", "snow")])):
        panels[name] = {**panels[members[0]], "images": [i for n in members for i in panels[n]["images"]],
                        "annotations": [a for n in members for a in panels[n]["annotations"]]}
    expected = {i["image_id"] for p in panels.values() for i in p["images"]}
    def compact(p):
        if p is None:
            return None
        return {k:p[k] for k in ("threshold", "image_count", "eligible_gt", "tp", "fp", "fn", "ignored", "recall", "fppi")} | {
            "zero_area_fp": sum(r.get("native_zero_area", False) for r in p["matches"])}
    def matched(p):
        return {r["annotation_id"] for r in p["matches"] if r["outcome"] == "TP"}
    public = dict(researcher="GPT Sol", base=code["base"], g0="PENDING", panels={}, source={},
                  runtime=public_runtime_status(status), code_record=code,
                  aggregation_code_record=dict(script_sha256=pilot.sha(__file__),
                                               baseline_script_sha256=pilot.sha(pilot.__file__)),
                  config_path="configs/research/information_control_20261111.json")
    private = {}
    points = {}
    for arm in ARMS:
        raw = pilot.read(root/"results"/(arm+".json"))
        coverage = raw["provenance"]["evaluated_image_ids"]
        assert len(coverage) == len(set(coverage)) == 700 and set(coverage) == expected
        files = sorted((root/"results").glob(arm+"_native_batch_*.json"))
        rows = [i for f in files for i in pilot.read(f)]
        assert len(files) == 88 and len(rows) == 700 and {i["image_id"] for i in rows} == expected
        assert sum(len(i["xyxy"]) for i in rows) == len(raw["predictions"])+len(raw["degenerate_predictions"])
        evs = {name:pilot.pilot_evaluator(panel, raw) for name,panel in panels.items()}
        selection = evs["source_selection"].select_threshold(.90)
        public["source"][arm] = {k:(compact(v) if k in ("operating_point", "candidate_ceiling") else v)
                                  for k,v in selection.items()}
        for name, ev in evs.items():
            ceiling = ev.operating_point()
            operating = ev.operating_point(selection["threshold"]) if selection["status"] == "FEASIBLE" else None
            points[name, arm] = ceiling
            public["panels"].setdefault(name, {})[arm] = dict(ceiling=compact(ceiling), operating=compact(operating))
    for name in panels:
        contrasts = {}
        for a,b,label in (("H1280", "L640", "H-L"), ("H1280", "U1280", "H-U"), ("U1280", "L640", "U-L")):
            ia, ib = matched(points[name,a]), matched(points[name,b])
            n = points[name,a]["eligible_gt"]
            contrasts[label] = dict(gained=len(ia-ib), lost=len(ib-ia), net_tp=len(ia)-len(ib),
                                    delta_recall=(len(ia)-len(ib))/n if n else None)
            private[name+"/"+label] = dict(gained=sorted(ia-ib), lost=sorted(ib-ia))
        public["panels"][name]["contrasts"] = contrasts
    c = public["panels"]["pooled_adverse"]["contrasts"]
    gain, recovered = c["H-L"]["net_tp"], c["U-L"]["net_tp"]
    public["primary"] = dict(rule="M_H>M_L and M_U-M_L >= .5*(M_H-M_L)>0", supports=gain>0 and 2*recovered>=gain,
        H_minus_L_tp=gain, U_minus_L_tp=recovered, H_minus_U_tp=c["H-U"]["net_tp"],
        fraction_recovered=recovered/gain if gain else None)
    operation = pilot.read(root/"operation.json")
    public["execution"] = {k:v for k,v in operation.items() if k not in ("events", "session")}
    public["hashes"] = {p.name:pilot.sha(p) for p in (root/"results").iterdir() if p.is_file()}
    public["hashes"]["evidence_final.tar.gz"] = pilot.sha(root/"evidence_final.tar.gz")
    public["validation"] = dict(exact_unique_images_per_arm=700, native_batches_per_arm=88,
        total_new_forward_images=2100, gt_map_example="PASS continuous edge map; retained privately",
        raw_batches_before_validation=True, zero_area="explicit FP, no repair/crowd absorption",
        pre_nms_instrumentation=False)
    public["limitations"] = [
        "Finite capped post-NMS pipeline, not detector capacity; cap-saturated rows retained.",
        "COCO source not verified clear/day; pretrained COCO exposure; no population guarantee.",
        "Provisional human union/crowd policy; dependent ACDC panels; no IID confidence intervals.",
        "H-U detail degradation at fixed grid; U-L enlargement including interpolation/anchors/NMS; neither isolates stride or causal darkness.",
        "No novel method, fusion/gating claim or standalone GPU cost comparison."]
    pilot.write(root/"gt_transitions_private.json", private)
    pilot.write(output, public)
    print(pilot.json.dumps(dict(primary=public["primary"], source={a:public["source"][a]["status"] for a in ARMS})))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["infer", "aggregate"])
    parser.add_argument("root")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.mode == "infer":
        infer(args.root)
    else:
        aggregate(args.root, args.output)
