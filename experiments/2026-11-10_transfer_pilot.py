"""GPT Sol's bounded frozen-model pilot; private packet/results stay under outputs/.

Local prepare/aggregate use only stdlib and the existing reference evaluator.
Remote infer uses native pinned Ultralytics predict; no training or cache replay.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import sys
import tarfile
import time
import traceback

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
SEED = "sol-transfer-pilot-2026-11-10-v1"
POLICIES = [dict(id="maximal", floor=.0001, cap=3000),
            dict(id="cap100", floor=.0001, cap=100),
            dict(id="cap300", floor=.0001, cap=300),
            dict(id="floor01", floor=.01, cap=3000)]
PY_SCHEMA = "threshold-transfer-v1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def order(image):
    return hashlib.sha256((SEED + "\n" + image["file_name"]).encode()).hexdigest()


def pilot_evaluator(panel, raw):
    """Positive geometry uses the reference matcher; native zero area is explicit FP."""
    from threshold_transfer.metrics import ReferenceEvaluator
    ids = {i["image_id"] for i in panel["images"]}
    coverage = raw["provenance"]["evaluated_image_ids"]
    assert len(coverage) == len(set(coverage)) and ids <= set(coverage)
    positive = [p for p in raw["predictions"] if p["image_id"] in ids]
    ev = ReferenceEvaluator(panel, dict(schema_version=PY_SCHEMA,
        provenance=dict(evaluated_image_ids=sorted(ids)), predictions=positive),
        categories=["human"], ignore_policy="same_category_ioa", bounds_policy="allow_outside")
    seen = {p["candidate_id"] for p in positive}
    for pred in raw.get("degenerate_predictions", []):
        if pred["image_id"] not in ids:
            continue
        x1,y1,x2,y2 = pred["native_xyxy"]
        assert all(math.isfinite(v) for v in [x1,y1,x2,y2,pred["score"]])
        assert x2 >= x1 and y2 >= y1 and (x2 == x1 or y2 == y1)
        assert pred["category"] == "human" and 0 <= pred["score"] <= 1
        assert pred["candidate_id"] not in seen
        seen.add(pred["candidate_id"])
        ev.rows.append(dict(candidate_id=pred["candidate_id"], image_id=pred["image_id"],
            category="human", score=pred["score"], outcome="FP", annotation_id=None,
            native_zero_area=True))
    ev.rows.sort(key=lambda p: (-p["score"], p["candidate_id"]))
    return ev


def native_subset(doc, images):
    ids = {i["id"] for i in images}
    return dict(images=images, annotations=[a for a in doc["annotations"] if a["image_id"] in ids],
                categories=doc["categories"])


def zero_area_check():
    """Tiny synthetic accounting check, not empirical evidence."""
    panel=dict(schema_version=PY_SCHEMA, provenance={},
        images=[dict(image_id="i",width=10,height=10),dict(image_id="empty",width=10,height=10)],
        annotations=[dict(annotation_id="g",image_id="i",category="human",bbox=[0,0,2,2],ignore=False,iscrowd=False),
            dict(annotation_id="crowd",image_id="i",category="human",bbox=[0,0,10,10],ignore=False,iscrowd=True)])
    tp=dict(candidate_id="z_tp",image_id="i",category="human",bbox=[0,0,2,2],score=.8)
    zero=dict(candidate_id="a_zero",image_id="i",category="human",bbox=[1,1,0,1],native_xyxy=[1,1,1,2],score=.8)
    raw=dict(predictions=[tp],degenerate_predictions=[zero],provenance=dict(evaluated_image_ids=["i","empty"]))
    for score in (.8,.9):
        zero["score"]=score
        ev=pilot_evaluator(panel,raw)
        chosen=ev.select_threshold(.9)
        point=chosen["operating_point"]
        assert chosen["threshold"]==.8 and (point["tp"],point["fp"],point["ignored"],point["fppi"]["value"])==(1,1,0,.5)
        assert ev.rows[0]["candidate_id"]=="a_zero" and point["binary_tp_ece"]["count"]==2
        assert chosen["boundary_tie_count"]==(2 if score==.8 else 1)
        assert ev.operating_point(math.nextafter(.8,1))["tp"]==0
    print("PASS synthetic TP + zero-area FP: score order, ties, inclusive boundary, FPPI, no crowd absorption, ECE")


def prepare(root):
    from threshold_transfer.data import convert_coco
    from threshold_transfer.acdc import AGGREGATE_FILES, convert_acdc, parse_file_name
    from threshold_transfer.metrics import ReferenceEvaluator
    root = Path(root)
    packet = root / "packet"
    packet.mkdir(parents=True, exist_ok=True)
    acdc_root = Path("C:/Users/Advait/autonomous-sys-research/data/acdc/extracted")
    coco_root = Path("C:/Users/Advait/det-eval-2d/datasets/coco")
    smoke_path = Path("C:/Users/Advait/ar-work/smoke/data/selection_manifest.json")
    smoke = read(smoke_path) if smoke_path.exists() else None
    exclude = set()
    if smoke:
        exclude.update(smoke["train_pool"]["image_ids"])
        exclude.update(i["image_id"] for i in smoke["selection"])
    coco_path = coco_root / "annotations/instances_val2017.json"
    coco = read(coco_path)
    ranked = sorted((i for i in coco["images"] if i["id"] not in exclude), key=order)
    panels, source_files, files = {}, [], []
    source_files.append(dict(kind="COCO annotation", sha256=sha(coco_path)))
    for name, images in (("source_selection", ranked[:256]), ("coco_reference", ranked[256:512])):
        panels[name] = convert_coco(native_subset(coco, images), dataset_tag="coco", split="val2017",
            ignore_policy="coco_iscrowd_v1_provisional", source={"sha256":sha(coco_path)})
        for image in panels[name]["images"]:
            original = coco_root / "val2017" / image["file_name"]
            image["file_name"] = "images/coco/" + image["file_name"]
            files.append((original, image["file_name"]))
    adverse_path = acdc_root / AGGREGATE_FILES[("val", False)]
    reference_path = acdc_root / AGGREGATE_FILES[("val", True)]
    adverse, reference = read(adverse_path), read(reference_path)
    refs_by_pair = {parse_file_name(i["file_name"])["pair_key"]: i for i in reference["images"]}
    source_files += [dict(kind="ACDC adverse val annotation", sha256=sha(adverse_path)),
                     dict(kind="ACDC normal val annotation", sha256=sha(reference_path))]
    for condition in ("fog", "night", "rain", "snow"):
        chosen = sorted([i for i in adverse["images"] if parse_file_name(i["file_name"])["condition"] == condition], key=order)[:32]
        pairs = [i for i in chosen if parse_file_name(i["file_name"])["pair_key"] in refs_by_pair]
        ref_images = [refs_by_pair[parse_file_name(i["file_name"])["pair_key"]] for i in pairs]
        for name, doc, ims, is_ref in ((condition, adverse, chosen, False),
                    (condition+"_paired", adverse, pairs, False),
                    (condition+"_normal", reference, ref_images, True)):
            panels[name] = convert_acdc(native_subset(doc, ims), split="val", reference=is_ref,
                ignore_policy="acdc_iscrowd_v1_provisional", check_masks=False)
            for image in panels[name]["images"]:
                original = acdc_root / "rgb_anon_trainvaltest/rgb_anon" / image["file_name"]
                image["file_name"] = "images/acdc/" + image["file_name"]
                files.append((original, image["file_name"]))
    for panel in panels.values():
        # An explicit zero-shot human task, never an implicit pedestrian alias.
        panel["annotations"] = [a for a in panel["annotations"] if a["category"] in ("person", "rider")]
        for a in panel["annotations"]:
            a.setdefault("attributes", {})["pilot_native_category"] = a["category"]
            a["category"] = "human"
    manifest = dict(seed=SEED, ordering="sha256(seed + newline + native file_name), ascending",
        excluded_smoke_images=len(exclude), smoke_manifest_sha256=sha(smoke_path) if smoke else None,
        source_files=source_files, panels=panels)
    write(packet / "manifest.json", manifest)
    config = dict(researcher="GPT Sol", base="6847916241d7a08444bdf4313bb7703c9e112ebd",
        seed=SEED, policies=POLICIES, objectives=[.8,.9,.95], imgsz=640, batch=8,
        half=False, rect=False, device="0", classes=[0], class_selection="native person-only before final cap",
        nms_iou=.7, agnostic_nms=False, augment=False, geometry="native xyxy converted to xywh; allow_outside; no repair",
        evaluator="threshold_transfer.metrics.ReferenceEvaluator; IoU .50; same_category_ioa .50 provisional",
        task="COCO person outputs/GT; ACDC person+rider merged human; diagnostic only",
        manifest_sha256=sha(packet/"manifest.json"), annotations=source_files,
        sample_counts={k:len(v["images"]) for k,v in panels.items()}, smoke_exclusions=len(exclude),
        budget=dict(max_CU=10,max_minutes=90,admission_CU_per_hour=6),
        H1="rho .90: abs(B_night)>abs(D_night) and abs(B_night)>abs(B_COCOref); infeasible => untestable",
        models={k: dict(sha256=v["sha256"]) for k,v in read(REPO/"configs/smoke/smoke_config.json")["models"].items() if k.startswith("yolo")})
    write(REPO/"configs/research/transfer_pilot_20261110.json", config)
    write(packet/"config.json", config)
    # One meaningful synthetic geometry/crowd sanity check, not research evidence.
    ann=dict(schema_version=PY_SCHEMA,provenance={},images=[dict(image_id="empty"),dict(image_id="a",width=10,height=10)],annotations=[
        dict(annotation_id="g",image_id="a",category="human",bbox=[-1,0,4,4],ignore=False,iscrowd=False),
        dict(annotation_id="crowd",image_id="a",category="human",bbox=[4,0,4,4],ignore=True,iscrowd=True)])
    pred=dict(schema_version=PY_SCHEMA,provenance={"evaluated_image_ids":["a","empty"]},predictions=[
        dict(candidate_id="p",image_id="a",category="human",bbox=[-1,0,4,4],score=.9),
        dict(candidate_id="c",image_id="a",category="human",bbox=[4,0,4,4],score=.8)])
    point=ReferenceEvaluator(ann,pred,categories=["human"],ignore_policy="same_category_ioa",bounds_policy="allow_outside").operating_point()
    assert (point["tp"],point["fp"],point["ignored"],point["image_count"]) == (1,0,1,2)
    with tarfile.open(root/"packet.tar", "w") as tar:
        tar.add(packet/"manifest.json", arcname="packet/manifest.json")
        tar.add(packet/"config.json", arcname="packet/config.json")
        tar.add(__file__, arcname="packet/experiments/2026-11-10_transfer_pilot.py")
        for path in (REPO/"src/threshold_transfer").glob("*.py"):
            tar.add(path,arcname="packet/src/threshold_transfer/"+path.name)
        for original, target in sorted(set(files),key=lambda x:x[1]):
            assert original.is_file(), original
            tar.add(original, arcname="packet/"+target)
        models=read(REPO/"configs/smoke/smoke_config.json")["models"]
        for model in ("yolo11s","yolo26s"):
            weight=Path(models[model]["weights"])
            assert sha(weight)==models[model]["sha256"]
            tar.add(weight,arcname="packet/"+model+".pt")
    write(root/"packet_record.json",dict(bytes=(root/"packet.tar").stat().st_size,sha256=sha(root/"packet.tar"),
        config_sha256=sha(packet/"config.json"),manifest_sha256=sha(packet/"manifest.json"),synthetic_check="PASS"))
    print(json.dumps(dict(packet_bytes=(root/"packet.tar").stat().st_size,panels=config["sample_counts"],excluded=len(exclude))))


def infer(root, model_name):
    import logging
    import torch
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.utils import LOGGER
    censored=[]
    class CensorLog(logging.Handler):
        def emit(self, record):
            message=record.getMessage()
            if "time limit" in message.lower() or "nan" in message.lower():
                censored.append(message)
    LOGGER.addHandler(CensorLog())
    root=Path(root)
    result=root/"results"
    result.mkdir(exist_ok=True)
    manifest=read(root/"manifest.json")
    config=read(root/"config.json")
    assert ultralytics.__version__ == "8.4.197"
    weight=root/(model_name.split("_")[0]+".pt")
    assert sha(weight)==config["models"][model_name.split("_")[0]]["sha256"]
    status=dict(status="RUNNING",model=model_name,coverage={},started=time.time(),policies=config["policies"],
        torch=torch.__version__,python=sys.version,ultralytics=ultralytics.__version__,checkpoint_sha256=sha(weight),
        device=torch.cuda.get_device_name(0),total_memory_bytes=torch.cuda.get_device_properties(0).total_memory)
    status_path=result/(model_name+"_status.json")
    write(status_path,status)
    try:
        model=YOLO(str(weight))
        head=model.model.model[-1]
        status["head_before"]=dict(type=type(head).__name__,end2end=getattr(head,"end2end",None),
            one2one_cv2=hasattr(head,"one2one_cv2"),one2one_cv3=hasattr(head,"one2one_cv3"),
            cv2=hasattr(head,"cv2"),cv3=hasattr(head,"cv3"))
        nms = model_name.endswith("_o2m") if model_name.startswith("yolo26") else None
        if model_name.startswith("yolo26"):
            assert all(status["head_before"][k] for k in ("one2one_cv2","one2one_cv3","cv2","cv3")), "both heads unavailable"
        from ultralytics.nn.modules import head as head_module
        from ultralytics.models.yolo.detect import predict as predict_module
        from ultralytics.nn.tasks import DetectionModel
        from ultralytics.utils import nms as nms_module
        for name,module in (("head",head_module),("predict",predict_module),("nms",nms_module)):
            (result/(model_name+"_"+name+"_source.py")).write_text(inspect.getsource(module),encoding="utf-8")
        (result/(model_name+"_fuse_source.py")).write_text(inspect.getsource(DetectionModel.fuse),encoding="utf-8")
        # Shared adverse rows are inferred once and reused only as identical panel membership.
        images={i["image_id"]:i for p in manifest["panels"].values() for i in p["images"]}
        images=list(images.values())
        status["expected_images"]=len(images)
        for policy in config["policies"]:
            torch.cuda.reset_peak_memory_stats()
            preds=[]; degenerates=[]; coverage=[]; measurement=[]
            begun=time.monotonic()
            for start in range(0,len(images),config["batch"]):
                batch=images[start:start+config["batch"]]
                kwargs=dict(conf=policy["floor"],max_det=policy["cap"],imgsz=config["imgsz"],
                    device=0,half=False,rect=False,batch=config["batch"],classes=[0],iou=.7,
                    agnostic_nms=False,augment=False,verbose=False,save=False,stream=True)
                if nms is not None:
                    kwargs["nms"]=nms
                outputs=list(model.predict([str(root/i["file_name"]) for i in batch],**kwargs))
                # Private raw capture intentionally permits nonfinite JSON tokens so even
                # invalid native values survive; validated/public documents remain strict.
                native = [dict(image_id=batch[j]["image_id"] if j < len(batch) else None,
                        xyxy=o.boxes.xyxy.detach().cpu().tolist(),
                        scores=o.boxes.conf.detach().cpu().tolist(),classes=o.boxes.cls.detach().cpu().tolist(),
                        speed=o.speed) for j,o in enumerate(outputs)]
                (result/(model_name+"_"+policy["id"]+f"_native_batch_{start:04d}.json")).write_text(
                    json.dumps(native, indent=2, allow_nan=True), encoding="utf-8")
                assert not censored, f"native output-stage censoring: {censored}"
                assert len(outputs)==len(batch), "incomplete native batch"
                for image,out in zip(batch,outputs):
                    assert Path(out.path).resolve()==(root/image["file_name"]).resolve()
                    assert tuple(out.orig_shape)==(image["height"],image["width"])
                    boxes=out.boxes.xyxy.detach().cpu().tolist()
                    scores=out.boxes.conf.detach().cpu().tolist()
                    classes=out.boxes.cls.detach().cpu().tolist()
                    assert len(boxes)==len(scores)==len(classes)
                    for j,(box,score,cls) in enumerate(zip(boxes,scores,classes)):
                        assert cls==0 and all(math.isfinite(v) for v in box+[score]) and 0 <= score <= 1
                        x1,y1,x2,y2=box
                        assert x2>=x1 and y2>=y1, "reversed native box; no repair allowed"
                        pred=dict(candidate_id=image["image_id"]+f":{j:04d}",image_id=image["image_id"],
                            category="human",bbox=[x1,y1,x2-x1,y2-y1],score=score)
                        if x2==x1 or y2==y1:
                            degenerates.append(dict(**pred,native_xyxy=box))
                        else:
                            preds.append(pred)
                    coverage.append(image["image_id"])
                    measurement.append(dict(image_id=image["image_id"],candidate_count=len(boxes),speed=out.speed))
                if start==0 or start%128==0:
                    print(json.dumps(dict(model=model_name,policy=policy["id"],complete=len(coverage),total=len(images))),flush=True)
            assert len(coverage)==len(images) and len(set(coverage))==len(images)
            status["coverage"][policy["id"]]=dict(complete=len(coverage),seconds=time.monotonic()-begun,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                candidate_count=len(preds)+len(degenerates),zero_area_count=len(degenerates),
                images_at_cap=sum(i["candidate_count"]==policy["cap"] for i in measurement))
            write(result/(model_name+"_"+policy["id"]+".json"),dict(schema_version=PY_SCHEMA,predictions=preds,
                degenerate_predictions=degenerates,
                provenance=dict(evaluated_image_ids=coverage,policy=policy,model=model_name),measurements=measurement))
            panel=manifest["panels"]["source_selection"]
            ev=pilot_evaluator(panel,dict(predictions=preds,degenerate_predictions=degenerates,
                provenance=dict(evaluated_image_ids=coverage)))
            point=ev.operating_point()
            print(json.dumps(dict(policy_complete=policy["id"],source_tp=point["tp"],source_gt=ev.gt_count,
                source_M=point["recall"]["value"],source_ceiling_FPPI=point["fppi"]["value"],
                objectives={str(r):ev.select_threshold(r)["status"] for r in config["objectives"]})),flush=True)
            predictor=model.predictor
            active_head=predictor.model.model.model[-1]
            status["effective_runtime"]=dict(nms=getattr(predictor.args,"nms",None),
                end2end=getattr(predictor.model,"end2end",None),head_end2end=getattr(active_head,"end2end",None),
                head_type=type(active_head).__name__,cv2=hasattr(active_head,"cv2"),cv3=hasattr(active_head,"cv3"),
                one2one_cv2=hasattr(active_head,"one2one_cv2"))
            if model_name.startswith("yolo26"):
                expected=not nms
                assert status["effective_runtime"]["end2end"]==expected and status["effective_runtime"]["head_end2end"]==expected, "head switch unconfirmed"
            write(status_path,status)
        status["status"]="COMPLETE"
    except BaseException as exc:
        status.update(status="ERROR",error=repr(exc),traceback=traceback.format_exc())
        if "coverage" in locals():
            status["partial_policy"]=policy["id"]
            status["validated_complete_images_in_partial_policy"]=len(coverage)
            write(result/(model_name+"_partial.json"),dict(predictions=preds,
                degenerate_predictions=degenerates,
                validated_complete_image_ids=coverage,status="INVALID_PARTIAL_NOT_FOR_EVALUATION"))
        raise
    finally:
        status["ended"]=time.time()
        write(status_path,status)
        print(json.dumps({k:v for k,v in status.items() if k not in ("traceback",)}),flush=True)


def aggregate(root, destination):
    from threshold_transfer.metrics import ReferenceEvaluator
    root=Path(root)
    manifest=read(root/"packet/manifest.json")
    results=root/"results"
    public=dict(researcher="GPT Sol",role="diagnostic",g0="PENDING",panels={},models={},
        manifest_sha256=sha(root/"packet/manifest.json"),
        aggregation_provenance=dict(script_sha256=sha(Path(__file__)),
            reference_evaluator_sha256=sha(REPO/"src/threshold_transfer/metrics.py"),
            geometry_accounting=read(root/"packet/config.json").get("zero_area_accounting")),
        limitations=["COCO is not verified clear/day; image disjointness does not establish training independence.",
            "ACDC scene/view dependencies; independent group count unknown; no IID intervals or primary BDD claim.",
            "Native finite-pipeline output ceilings, not detector capacity; no completeness certificate.",
            "Person-only native predict classes=[0]; O2O head-level top-k may precede person filtering.",
            "Provisional merged-human and crowd ignore policies; no official-AP equivalence."])
    # This execution's records only. Historical failure evidence remains separate.
    launch_root=root
    if (launch_root/"packet_record.json").exists():
        public["original_packet_record"]=read(launch_root/"packet_record.json")
    if (launch_root/"code_record.json").exists():
        public["sent_code_record"]=read(launch_root/"code_record.json")
    if (root/"operation.json").exists():
        operation=read(root/"operation.json")
        def observed(log,pattern):
            path=Path(log)
            match=re.search(pattern,path.read_text(encoding="utf-8")) if path.exists() else None
            return float(match.group(1)) if match else None
        before=observed(launch_root/"before_usage.log",r"Current balance:\s*([\d.]+)")
        after=observed(root/"final_usage.log",r"Current balance:\s*([\d.]+)")
        active=observed(root/"final_usage.log",r"Active assignments:\s*(\d+)")
        rate=observed(root/"final_usage.log",r"Usage rate:\s*([\d.]+)")
        public["execution"]=dict(status=operation["status"],first_allocation_utc=operation.get("first_allocation_requested_utc"),
            ended_utc=operation.get("ended_utc"),outer_elapsed_seconds=operation.get("elapsed_seconds"),
            admission_CU_hr=operation.get("admission_rate_CU_hr"),
            displayed_balance_before_CU=before,displayed_balance_after_CU=after,
            displayed_delta_CU=round(before-after,2) if before is not None and after is not None else None,
            final_active_assignments=active,final_usage_rate_CU_hr=rate,
            owned_teardown_verified=operation.get("owned_teardown_verified",False),
            failure_sequence=operation.get("failures",[]),
            direct_process_returncode=operation.get("direct_process_returncode"),
            prior_displayed_CU=0.31,prior_failure_note="2026-11-10_sol_results.md",
            optional_models_not_run=["yolo26s_o2o","yolo26s_o2m"])
    for name,panel in manifest["panels"].items():
        eligible=[a for a in panel["annotations"] if not(a["ignore"] or a["iscrowd"])]
        counts=collections.Counter(a["image_id"] for a in eligible)
        public["panels"][name]=dict(images=len(panel["images"]),gt=len(eligible),
            empty_human_images=sum(counts[i["image_id"]]==0 for i in panel["images"]),
            crowd_regions=sum(a["iscrowd"] for a in panel["annotations"]),
            native_gt_categories=dict(collections.Counter(a["attributes"]["pilot_native_category"] for a in eligible)))
    def compact(point):
        result={k:v for k,v in point.items() if k not in ("matches","binary_tp_ece")}
        zero=sum(r.get("native_zero_area",False) for r in point["matches"])
        result.update(zero_area_fp=zero,zero_area_fppi=zero/point["image_count"],
            binary_tp_ece={k:v for k,v in point["binary_tp_ece"].items() if k!="bins"})
        return result
    def val(point,key="recall"):
        return point[key]["value"] if point else None
    def sub(x,y):
        return x-y if x is not None and y is not None else None
    for status_path in results.glob("*_status.json"):
        status=read(status_path)
        if "model" not in status:
            continue
        name=status["model"]
        model=dict(status=status,policies={})
        if status["status"]=="COMPLETE" and (root/"operation.json").exists():
            assert read(root/"operation.json").get("direct_process_returncode")==0
            assert read(results/"process_status.json")["returncode"]==0
        model["captured_source_sha256"]={p.name:sha(p) for p in results.glob(name+"_*_source.py")}
        public["models"][name]=model
        evaluators={}
        for policy in POLICIES:
            pred_path=results/(name+"_"+policy["id"]+".json")
            if not pred_path.exists():
                continue
            raw=read(pred_path)
            coverage=raw["provenance"]["evaluated_image_ids"]
            expected={i["image_id"] for p in manifest["panels"].values() for i in p["images"]}
            assert len(coverage)==len(expected) and set(coverage)==expected
            assert status["coverage"][policy["id"]]["complete"]==len(expected)
            assert len(raw["predictions"])+len(raw.get("degenerate_predictions",[]))==sum(
                m["candidate_count"] for m in raw["measurements"])
            assert status["coverage"][policy["id"]]["candidate_count"]==sum(m["candidate_count"] for m in raw["measurements"])
            assert status["coverage"][policy["id"]]["zero_area_count"]==len(raw.get("degenerate_predictions",[]))
            policy_evaluators={}
            for panel_name,panel in manifest["panels"].items():
                policy_evaluators[panel_name]=pilot_evaluator(panel,raw)
            evaluators[policy["id"]]=policy_evaluators
        for policy_id,evs in evaluators.items():
            policy_result=dict(ceilings={p:compact(e.operating_point()) for p,e in evs.items()},objectives={})
            model["policies"][policy_id]=policy_result
            for rho in (.8,.9,.95):
                selection=evs["source_selection"].select_threshold(rho)
                baseline=evaluators["maximal"]["source_selection"].select_threshold(rho)
                summary={k:v for k,v in selection.items() if k not in ("candidate_ceiling","operating_point")}
                summary["source_selection_operating"]=compact(selection["operating_point"]) if selection["operating_point"] else None
                summary["panels"]={}
                for p,e in evs.items():
                    reselected=e.operating_point(selection["threshold"]) if selection["status"]=="FEASIBLE" else None
                    fixed=e.operating_point(baseline["threshold"]) if baseline["status"]=="FEASIBLE" else None
                    base_e=evaluators["maximal"][p]
                    base=base_e.operating_point(baseline["threshold"]) if baseline["status"]=="FEASIBLE" else None
                    ceiling=val(e.operating_point())
                    point=dict(reselected=compact(reselected) if reselected else None,fixed_maximal_threshold=compact(fixed) if fixed else None,
                        M=ceiling,W_reselected=sub(ceiling,val(reselected)),W_fixed=sub(ceiling,val(fixed)),
                        B=sub(val(reselected),val(fixed)),D=sub(val(fixed),val(base)))
                    point["signed_count_changes"]={k:dict(B=sub(reselected[k] if reselected else None,fixed[k] if fixed else None),
                        D=sub(fixed[k] if fixed else None,base[k] if base else None)) for k in ("tp","fp")}
                    if p!="source_selection":
                        ref=evs["coco_reference"]
                        ref_point=ref.operating_point(selection["threshold"]) if reselected else None
                        point["coco_reference_minus_reselected"]=sub(val(ref_point),val(reselected))
                        point["coco_reference_M_minus_M"]=sub(val(ref.operating_point()),ceiling)
                        point["coco_reference_W_minus_W_reselected"]=sub(sub(val(ref.operating_point()),val(ref_point)),point["W_reselected"])
                        ref_fixed=ref.operating_point(baseline["threshold"]) if fixed else None
                        point["coco_reference_minus_fixed"]=sub(val(ref_fixed),val(fixed))
                        point["coco_reference_W_minus_W_fixed"]=sub(sub(val(ref.operating_point()),val(ref_fixed)),point["W_fixed"])
                    if p.endswith("_paired"):
                        normal=evs[p.removesuffix("_paired")+"_normal"]
                        n_point=normal.operating_point(selection["threshold"]) if reselected else None
                        point["paired_normal_minus_adverse"]=sub(val(n_point),val(reselected))
                        point["paired_normal_M_minus_adverse_M"]=sub(val(normal.operating_point()),ceiling)
                        point["paired_normal_W_minus_adverse_W"]=sub(sub(val(normal.operating_point()),val(n_point)),point["W_reselected"])
                    summary["panels"][p]=point
                policy_result["objectives"][str(rho)]=summary
        h1=[]
        for policy_id,policy_result in model["policies"].items():
            if policy_id=="maximal":
                continue
            objective=policy_result["objectives"]["0.9"]
            night=objective["panels"]["night"]; ref=objective["panels"]["coco_reference"]
            feasible=objective["status"]=="FEASIBLE" and all(x is not None for x in (night["B"],night["D"],ref["B"]))
            h1.append(dict(policy=policy_id,status="TESTABLE" if feasible else "UNTESTABLE",
                satisfies=abs(night["B"])>abs(night["D"]) and abs(night["B"])>abs(ref["B"]) if feasible else None,
                B_night=night["B"],D_night=night["D"],B_coco_reference=ref["B"]))
        model["H1"]=h1
        model["H1_verdict"]=("SUPPORT_IN_AT_LEAST_ONE_PRESPECIFIED_CONTRAST" if any(h["satisfies"] for h in h1)
            else "NO_SUPPORT" if any(h["status"]=="TESTABLE" for h in h1) else "UNTESTABLE")
        if not evaluators:
            model["policies"]={p["id"]:dict(status="INVALID_PARTIAL" if p["id"]=="maximal" else "NOT_RUN",
                validated_complete_policy_images=0,expected_images=status["expected_images"],
                objectives={str(r):dict(status="UNAVAILABLE_NO_VALID_COVERAGE",threshold=None)
                    for r in (.8,.9,.95)}) for p in POLICIES}
            model["H1"]=[dict(policy=p["id"],status="UNTESTABLE",satisfies=None,
                reason="No complete native policy coverage; not a source-infeasibility result")
                for p in POLICIES if p["id"]!="maximal"]
        else:
            for policy_id,policy_result in model["policies"].items():
                policy_result["ceiling_changes_from_maximal"]={}
                for panel,point in policy_result["ceilings"].items():
                    base=model["policies"]["maximal"]["ceilings"][panel]
                    policy_result["ceiling_changes_from_maximal"][panel]={
                        "tp":point["tp"]-base["tp"], "fp":point["fp"]-base["fp"],
                        "recall":sub(val(point),val(base)), "fppi":sub(val(point,"fppi"),val(base,"fppi"))}
    write(destination,public)
    print(json.dumps(dict(panels=public["panels"],models={k:dict(status=v["status"]["status"],H1=v["H1"],
        source_M={p:r["ceilings"]["source_selection"]["recall"]["value"] for p,r in v["policies"].items() if "ceilings" in r}) for k,v in public["models"].items()})))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["prepare","infer","aggregate","zero-area-check"])
    parser.add_argument("root")
    parser.add_argument("--model",default="yolo11s")
    parser.add_argument("--output")
    args=parser.parse_args()
    if args.mode=="zero-area-check": zero_area_check()
    elif args.mode=="prepare": prepare(args.root)
    elif args.mode=="infer": infer(args.root,args.model)
    else: aggregate(args.root,args.output)
