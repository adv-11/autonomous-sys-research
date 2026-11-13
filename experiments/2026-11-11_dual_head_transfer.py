"""GPT Sol: fixed-panel native YOLO26 head-pipeline comparison; no training.

Private manifests, native batches and identifiers remain in ignored outputs.
Reuses the original pilot inference/evaluator, with first-batch branch evidence.
"""
from __future__ import annotations
import argparse
import collections
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import tarfile

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pilot", Path(__file__).with_name("2026-11-10_transfer_pilot.py"))
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
read, write, sha = pilot.read, pilot.write, pilot.sha
WEIGHT_SHA = "646f8bc3fe0a656803d95c294f7852321748cb29d13466a1af8862e2db384a1b"
PRIVATE = Path("C:/Users/Advait/autonomous-sys-research")


def prepare(root):
    from threshold_transfer.acdc import AGGREGATE_FILES, convert_acdc, parse_file_name
    root = Path(root)
    packet = root / "packet"
    packet.mkdir(parents=True, exist_ok=True)
    old_path = PRIVATE / "outputs/colab/empirical_20261110/packet/manifest.json"
    old = read(old_path)
    acdc = PRIVATE / "data/acdc/extracted"
    adverse_path = acdc / AGGREGATE_FILES[("val", False)]
    normal_path = acdc / AGGREGATE_FILES[("val", True)]
    adverse, normal = read(adverse_path), read(normal_path)
    previous = {i["file_name"].removeprefix("images/acdc/")
                for c in ("fog", "night", "rain", "snow") for i in old["panels"][c]["images"]}
    assert len(previous) == 128
    all_paths = [i["file_name"] for i in adverse["images"]]
    assert len(all_paths) == len(set(all_paths)) and previous <= set(all_paths)
    remaining = [i for i in adverse["images"] if i["file_name"] not in previous]
    assert len(remaining) == 278
    refs = {parse_file_name(i["file_name"])["pair_key"]: i for i in normal["images"]}
    assert len(refs) == len(normal["images"])
    panels = {k: old["panels"][k] for k in ("source_selection", "coco_reference")}
    for c in ("fog", "night", "rain", "snow"):
        chosen = sorted([i for i in remaining if parse_file_name(i["file_name"])["condition"] == c], key=lambda i:i["file_name"])
        paired = [i for i in chosen if parse_file_name(i["file_name"])["pair_key"] in refs]
        normal_images = {refs[parse_file_name(i["file_name"])["pair_key"]]["file_name"]:
                         refs[parse_file_name(i["file_name"])["pair_key"]] for i in paired}
        for name, doc, images, reference in ((c, adverse, chosen, False),
                (c+"_paired", adverse, paired, False), (c+"_normal", normal, list(normal_images.values()), True)):
            panel = convert_acdc(pilot.native_subset(doc, images), split="val", reference=reference,
                ignore_policy="acdc_iscrowd_v1_provisional", check_masks=False)
            panel["annotations"] = [a for a in panel["annotations"] if a["category"] in ("person", "rider")]
            for a in panel["annotations"]:
                a.setdefault("attributes", {})["pilot_native_category"] = a["category"]
                a["category"] = "human"
            for i in panel["images"]:
                i["file_name"] = "images/acdc/" + i["file_name"]
            panels[name] = panel
    for name, panel in panels.items():
        assert len({i["file_name"] for i in panel["images"]}) == len(panel["images"])
        assert {a["category"] for a in panel["annotations"]} <= {"human"}
        assert {a["attributes"]["pilot_native_category"] for a in panel["annotations"]} <= {"person", "rider"}
    manifest = dict(researcher="GPT Sol", base="c883688c641c021d2204d4555fbb689d122717b1",
        original_manifest_sha256=sha(old_path), original_source_eligibility=old,
        selection="All official adverse val paths minus original development128; available annotated references; unique native paths per panel; no GT selection",
        source_files=[dict(kind="ACDC adverse val",sha256=sha(adverse_path)),dict(kind="ACDC normal val",sha256=sha(normal_path))], panels=panels)
    # Keep original eligibility/provenance without embedding the obsolete panels.
    manifest["original_source_eligibility"] = {k:v for k,v in old.items() if k != "panels"}
    write(packet/"manifest.json", manifest)
    config = dict(researcher="GPT Sol", base=manifest["base"], manifest_sha256=sha(packet/"manifest.json"),
        policies=[dict(id="maximal",floor=.0001,cap=3000)], objectives=[.9], imgsz=1280,batch=8,
        half=False,rect=False,classes=[0],nms_iou=.7,agnostic_nms=False,augment=False,
        geometry="Native original-image preprocessing and original-coordinate outputs; allow_outside",
        task="COCO person; ACDC person+rider explicitly merged human; IoU .50; provisional crowd IoA .50",
        zero_area_accounting="Raw before validation; zero-area native boxes explicit FP, no crowd absorption",
        models=dict(yolo26s=dict(sha256=WEIGHT_SHA)),heads=dict(yolo26s_o2o=False,yolo26s_o2m=True),
        implementation="ultralytics==8.4.197",sample_counts={k:len(p["images"]) for k,p in panels.items()},
        H4=dict(objective=.90,both_source_feasible=True,absolute_coco_reference_gap_at_most=.02,
                absolute_new_night_gap_at_least=.05,interpretation="finite-panel screen, not statistical equivalence"),
        budget=dict(max_minutes=40,max_admission_CU_hr=6,cumulative_existing_CU=10,
                    prior_displayed_CU=1.28,meter_lag_reserve_CU=.3,no_top_up=True))
    write(packet/"config.json",config)
    write(REPO/"configs/research/dual_head_transfer_20261111.json",config)
    images = {i["file_name"]:i for p in panels.values() for i in p["images"]}
    weight=Path("C:/Users/Advait/ar-work/weights/yolo26s.pt")
    assert sha(weight)==WEIGHT_SHA
    with tarfile.open(root/"packet.tar", "w") as tar:
        for name in ("manifest.json","config.json"):
            tar.add(packet/name,arcname="packet/"+name)
        for name in ("2026-11-10_transfer_pilot.py","2026-11-11_dual_head_transfer.py"):
            tar.add(Path(__file__).with_name(name),arcname="packet/experiments/"+name)
        for path in (REPO/"src/threshold_transfer").glob("*.py"):
            tar.add(path,arcname="packet/src/threshold_transfer/"+path.name)
        tar.add(weight,arcname="packet/yolo26s.pt")
        for name in sorted(images):
            native = (Path("C:/Users/Advait/det-eval-2d/datasets/coco/val2017")/name.removeprefix("images/coco/")) if name.startswith("images/coco/") else acdc/"rgb_anon_trainvaltest/rgb_anon"/name.removeprefix("images/acdc/")
            assert native.is_file(),native
            tar.add(native,arcname="packet/"+name)
    chunks=root/"chunks"
    chunks.mkdir(exist_ok=True)
    with (root/"packet.tar").open("rb") as source:
        n=0
        while data:=source.read(4*1024**2):
            (chunks/f"part{n:04d}").write_bytes(data);n+=1
    record=dict(bytes=(root/"packet.tar").stat().st_size,sha256=sha(root/"packet.tar"),
        manifest_sha256=sha(packet/"manifest.json"),config_sha256=sha(packet/"config.json"),
        script_sha256=sha(__file__),baseline_sha256=sha(Path(pilot.__file__)),
        unique_images=len(images),chunks=n,check="PASS: exact source/ref equality, remaining278, unique paths and human class map",
        planning_transfer_minutes=(root/"packet.tar").stat().st_size/490741760*11.0,
        planning_total_minutes=(root/"packet.tar").stat().st_size/490741760*11.0+8,
        planning_CU_40minutes_at_last_rate=40/60*1.94)
    write(root/"packet_record.json",record)
    print(json.dumps(dict(record=record,panels=config["sample_counts"])))


def infer(root):
    pilot.require_colab()
    # Reuse the pilot body, adding read-only runtime hooks and source capture.
    # No learned branch, geometry or selection implementation is patched.
    body=inspect.getsource(pilot.infer)
    body=body.replace('        nms = model_name.endswith', '''        calls = {"o2m": 0, "o2o": 0}
        handles = []
        def count_branch(key):
            def hook(module, args, output): calls[key] += 1
            return hook
        for key, attr in (("o2m", "cv2"), ("o2o", "one2one_cv2")):
            for module in getattr(head, attr, []):
                handles.append(module.register_forward_hook(count_branch(key)))
        from ultralytics.nn.autobackend import AutoBackend
        (result/(model_name+"_backend_source.py")).write_text(inspect.getsource(AutoBackend), encoding="utf-8")
        nms = model_name.endswith''')
    # Raw output is saved before branch checks and native value validation.
    body=body.replace('                assert not censored', '''                if start == 0:
                    predictor=model.predictor
                    active=predictor.model.model.model[-1]
                    status["first_batch_branch_verification"]=dict(calls=calls.copy(),
                        backend_end2end=predictor.model.end2end, head_end2end=active.end2end,
                        head_max_det=getattr(active,"max_det",None), head_max_nms=getattr(active,"max_nms",None),
                        cv2_present=getattr(active,"cv2",None) is not None,
                        one2one_present=getattr(active,"one2one_cv2",None) is not None,
                        resolved_args=vars(predictor.args),
                        first_batch_counts=[len(o.boxes) for o in outputs])
                    write(status_path,status)
                    assert predictor.model.end2end == (not nms) and active.end2end == (not nms), "unsupported branch switch"
                    wanted="o2m" if nms else "o2o"
                    other="o2o" if nms else "o2m"
                    assert calls[wanted] > 0 and calls[other] == 0, "unexpected executed branch"
                    for handle in handles: handle.remove()
                assert not censored''')
    namespace=vars(pilot).copy()
    exec(compile(body, str(__file__)+":pilot_infer_with_evidence", "exec"),namespace)
    for head in ("yolo26s_o2o","yolo26s_o2m"):
        namespace["infer"](root,head)


def aggregate(root, destination):
    root=Path(root)
    manifest=read(root/"packet/manifest.json")
    result=dict(researcher="GPT Sol",g0="PENDING",config=read(root/"packet/config.json"),
        packet=read(root/"packet_record.json"),
        execution={k:v for k,v in read(root/"operation.json").items() if k not in ("events","packet","session")},
        panels={},heads={},contrasts={})
    result["controller_sha256"]=sha(root/"operate.py")
    result["aggregation_script_sha256"]=sha(__file__)
    result["retrieved_evidence"]=dict(sha256=sha(root/"evidence_final.tar.gz"),
        bytes=(root/"evidence_final.tar.gz").stat().st_size,
        native_batch_files=len(list((root/"results").glob("*_native_batch_*.json"))),
        process_status=read(root/"results/process_status.json"))
    expected={i["image_id"] for p in manifest["panels"].values() for i in p["images"]}
    assert read(root/"results/process_status.json")["returncode"]==0
    covered={}
    for head in ("yolo26s_o2o","yolo26s_o2m"):
        status=read(root/"results"/(head+"_status.json"))
        # Full resolved training/checkpoint defaults stay in private runtime evidence.
        args=status["first_batch_branch_verification"]["resolved_args"]
        status["first_batch_branch_verification"]["resolved_args"]={k:args[k] for k in (
            "task","mode","batch","imgsz","device","rect","conf","iou","max_det",
            "quantize","nms","classes","agnostic_nms","augment","save","verbose","compile")}
        raw=read(root/"results"/(head+"_maximal.json"))
        ids=raw["provenance"]["evaluated_image_ids"]
        assert status["status"]=="COMPLETE" and len(ids)==len(set(ids))==len(expected) and set(ids)==expected
        ev=pilot.pilot_evaluator(manifest["panels"]["source_selection"],raw)
        selected=ev.select_threshold(.9)
        selected.pop("operating_point",None)
        selected["candidate_ceiling"].pop("matches",None)
        selected["candidate_ceiling"]["binary_tp_ece"].pop("bins",None)
        counts=[m["candidate_count"] for m in raw["measurements"]]
        result["heads"][head]=dict(status=status,source_selection=selected,panels={},
            implementation_source_sha256={p.name:sha(p) for p in (root/"results").glob(head+"_*source.py")},
            realized_limits=dict(max_emitted_per_image=max(counts),total_emitted=sum(counts),
                images_at_requested_cap=sum(c==3000 for c in counts),
                images_equal_head_budget=sum(c==status["first_batch_branch_verification"]["head_max_det"] for c in counts)))
        covered[head]={}
        for name,panel in manifest["panels"].items():
            ev=pilot.pilot_evaluator(panel,raw)
            ceiling=ev.operating_point()
            operating=ev.operating_point(selected["threshold"]) if selected["status"]=="FEASIBLE" else None
            def compact(point):
                if point is None: return None
                value={k:v for k,v in point.items() if k not in ("matches","binary_tp_ece")}
                value["binary_tp_ece"]={k:v for k,v in point["binary_tp_ece"].items() if k!="bins"}
                value["native_zero_area_fp"]=sum(r.get("native_zero_area",False) for r in point["matches"])
                return value
            M=ceiling["recall"]["value"]
            r=operating["recall"]["value"] if operating else None
            panel_ids={i["image_id"] for i in panel["images"]}
            panel_counts=[m["candidate_count"] for m in raw["measurements"] if m["image_id"] in panel_ids]
            result["heads"][head]["panels"][name]=dict(ceiling=compact(ceiling),operating=compact(operating),
                M=M,r=r,W=M-r if M is not None and r is not None else None,
                max_emitted_per_image=max(panel_counts,default=0),
                images_at_requested_cap=sum(c==3000 for c in panel_counts))
            covered[head][name]={r["annotation_id"] for r in ceiling["matches"] if r["outcome"]=="TP"}
            result["panels"][name]=dict(images=len(panel["images"]),gt=ev.gt_count,
                native_gt_categories=dict(collections.Counter(a["attributes"]["pilot_native_category"] for a in panel["annotations"] if not(a["ignore"] or a["iscrowd"]))),
                crowd=sum(a["iscrowd"] for a in panel["annotations"]))
    def sub(a,b): return a-b if a is not None and b is not None else None
    for name in manifest["panels"]:
        a=result["heads"]["yolo26s_o2o"]["panels"][name]
        b=result["heads"]["yolo26s_o2m"]["panels"][name]
        ca,cb=covered["yolo26s_o2o"][name],covered["yolo26s_o2m"][name]
        result["contrasts"][name]=dict(orientation="O2O minus O2M",recall_gap=sub(a["r"],b["r"]),
            ceiling_gap=sub(a["M"],b["M"]),W_gap=sub(a["W"],b["W"]),
            ceiling_shared=len(ca&cb),ceiling_only_o2o=len(ca-cb),ceiling_only_o2m=len(cb-ca))
    feasible=all(h["source_selection"]["status"]=="FEASIBLE" for h in result["heads"].values())
    coco=result["contrasts"]["coco_reference"]["recall_gap"]
    night=result["contrasts"]["night"]["recall_gap"]
    result["H4"]=dict(verdict="UNTESTABLE" if not feasible or coco is None or night is None else
        "SUPPORT" if abs(coco)<=.02 and abs(night)>=.05 else "NO SUPPORT",
        both_source_feasible=feasible,absolute_coco_reference_gap=abs(coco) if coco is not None else None,
        absolute_new_night_gap=abs(night) if night is not None else None)
    write(destination,result)
    print(json.dumps(result["H4"]))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","infer","aggregate"])
    parser.add_argument("root")
    parser.add_argument("--destination")
    args=parser.parse_args()
    if args.action=="prepare": prepare(args.root)
    elif args.action=="infer": infer(args.root)
    else: aggregate(args.root,args.destination)
