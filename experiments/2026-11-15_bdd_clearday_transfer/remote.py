"""Claude Opus: Colab-side stages for the BDD clear-day transfer experiment.

    python remote.py setup                      # download+verify mirror archive, extract, write YOLO dataset
    python remote.py train --name pilot --epochs 1 [--fraction F]
    python remote.py train --name main --epochs N [--resume]
    python remote.py infer --weights W --out preds.npz

Native Ultralytics training/inference only. Runs from /content/packet. Images come
from the pinned Hugging Face mirror (publisher identity unverified) and are
accepted only with the frozen SHA-256. Labels are BDD100K legacy 2018 labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

PACKET = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKET))
import common as C  # noqa: E402

ROOT = Path("/content")
DATA = ROOT / "data"
RUNS = ROOT / "runs"
CFG = json.loads((PACKET / "config.json").read_text())


def log(**kw):
    print(json.dumps({"utc": time.strftime("%H:%M:%S", time.gmtime()), **kw}), flush=True)


def sha_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def setup():
    import urllib.request
    t0 = time.time()
    for fname, digest in CFG["manifest_sha256"].items():
        if fname.startswith("manifest_") or fname.startswith("yolo_"):
            assert sha_file(PACKET / fname) == digest, f"packet {fname} hash mismatch"
    train = json.loads((PACKET / "manifest_source_train.json").read_text())
    sel = json.loads((PACKET / "manifest_selection.json").read_text())
    val = json.loads((PACKET / "manifest_val.json").read_text())
    yolo = json.loads((PACKET / "yolo_labels_source.json").read_text())
    archive = ROOT / "bdd100k_images_100k.zip"
    if not archive.exists() or sha_file(archive) != CFG["images"]["archive_sha256"]:
        h = hashlib.sha256()
        tmp = archive.with_suffix(".part")
        with urllib.request.urlopen(CFG["images"]["url"], timeout=120) as r, open(tmp, "wb") as f:
            n = 0
            while chunk := r.read(16 << 20):
                f.write(chunk)
                h.update(chunk)
                n += len(chunk)
                if n % (1 << 30) < (16 << 20):
                    log(stage="download", gib=round(n / 2**30, 2), s=round(time.time() - t0))
        got = h.hexdigest()
        if got != CFG["images"]["archive_sha256"]:
            raise SystemExit(f"archive SHA-256 mismatch: {got}")
        tmp.rename(archive)
    t_dl = time.time() - t0
    log(stage="archive_verified", sha256=CFG["images"]["archive_sha256"], seconds=round(t_dl))
    want = {f"100k/train/{n}.jpg": "train" for n in train + sel}
    want.update({f"100k/val/{n}.jpg": "val" for n in val})
    nightcal_path = PACKET / "manifest_nightcal.json"  # amendment 4: BDD train-night calibration set
    if nightcal_path.exists():
        rec = json.loads((PACKET / "nightcal_manifest_record.json").read_text())
        assert sha_file(nightcal_path) == rec["manifest_sha256"], "nightcal manifest hash mismatch"
        want.update({f"100k/train/{n}.jpg": "nightcal" for n in json.loads(nightcal_path.read_text())})
    from PIL import Image
    dims_bad = 0
    with zipfile.ZipFile(archive) as z:
        members = {i.filename: i for i in z.infolist()}
        missing = [m for m in want if m not in members]
        assert not missing, f"{len(missing)} manifest images missing from archive"
        for member, split in want.items():
            dest = DATA / "images" / split / Path(member).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(z.read(members[member]))
            with Image.open(dest) as im:
                dims_bad += im.size != (C.WIDTH, C.HEIGHT)
    assert dims_bad == 0, f"{dims_bad} images are not 1280x720"
    for name, text in yolo.items():
        p = DATA / "labels" / "train" / f"{name}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (DATA / "source_train.txt").write_text("".join(f"{DATA}/images/train/{n}.jpg\n" for n in train))
    (DATA / "selection.txt").write_text("".join(f"{DATA}/images/train/{n}.jpg\n" for n in sel))
    (DATA / "data.yaml").write_text(
        f"path: {DATA}\ntrain: {DATA}/source_train.txt\nval: {DATA}/selection.txt\n"
        "names:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(C.CLASSES)))
    summary = {"status": "PASS", "download_and_verify_s": round(t_dl), "total_s": round(time.time() - t0),
               "extracted": len(want), "train": len(train), "selection": len(sel), "val": len(val),
               "all_1280x720": True}
    (ROOT / "setup_summary.json").write_text(json.dumps(summary))
    log(stage="setup_done", **summary)


ACDC_API = "https://acdc.vision.ee.ethz.ch/api"
ACDC = ROOT / "acdc"
ACDC_GT = {"gt_detection_trainval.zip": ("instancesonly_train_gt_detection.json", "instancesonly_val_gt_detection.json"),
           "gt_detection_trainval_ref.zip": ("instancesonly_train_gt_ref_detection.json",
                                             "instancesonly_val_gt_ref_detection.json")}


def acdc_fetch(entry):
    """Direct download from the ACDC package API (unauthenticated token), SHA-256 checked."""
    import urllib.request
    dest = ACDC / entry["file_name"]
    if dest.exists() and sha_file(dest) == entry["sha256"]:
        return dest
    with urllib.request.urlopen(f"{ACDC_API}/getPackageUri/{entry['package_id']}", timeout=60) as r:
        token = json.loads(r.read())["token"]
    h, n, t0 = hashlib.sha256(), 0, time.time()
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(f"{ACDC_API}/downloadPackage/{token}/{entry['file_name']}", timeout=300) as r, \
            open(tmp, "wb") as f:
        while chunk := r.read(16 << 20):
            f.write(chunk)
            h.update(chunk)
            n += len(chunk)
            if n % (1 << 30) < (16 << 20):
                log(stage="acdc_download", file=entry["file_name"], gib=round(n / 2**30, 2), s=round(time.time() - t0))
    if h.hexdigest() != entry["sha256"] or n != entry["bytes"]:
        raise SystemExit(f"ACDC {entry['file_name']} SHA-256/size mismatch: {h.hexdigest()} {n}")
    tmp.rename(dest)
    log(stage="acdc_verified", file=entry["file_name"], bytes=n, seconds=round(time.time() - t0))
    return dest


def acdc_setup():
    t0 = time.time()
    ACDC.mkdir(parents=True, exist_ok=True)
    man = {a["file_name"]: a for a in json.loads((PACKET / "acdc_archive_manifest.json").read_text())["archives"]}
    items = []
    for zname, jsons in ACDC_GT.items():
        with zipfile.ZipFile(acdc_fetch(man[zname])) as z:
            members = {Path(m).name: m for m in z.namelist()}
            for j in jsons:
                doc = json.loads(z.read(members[j]))
                role = ("ref_" if "_ref_" in j else "adverse_") + ("train" if "_train_" in j else "val")
                items += [{"role": role, "name": im["file_name"]} for im in doc["images"]]
    rgb = acdc_fetch(man["rgb_anon_trainvaltest.zip"])
    with zipfile.ZipFile(rgb) as z:
        members = {m.split("rgb_anon/", 1)[-1]: m for m in z.namelist() if not m.endswith("/")}
        missing = [i["name"] for i in items if i["name"] not in members]
        assert not missing, f"{len(missing)} labelled ACDC images missing from archive"
        for i in items:
            dest = ACDC / "images" / i["name"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(z.read(members[i["name"]]))
    (ACDC / "list.json").write_text(json.dumps(items))
    summary = {"status": "PASS", "images": len(items), "seconds": round(time.time() - t0),
               "roles": {r: sum(i["role"] == r for i in items) for r in sorted({i["role"] for i in items})}}
    (ROOT / "acdc_setup_summary.json").write_text(json.dumps(summary))
    log(stage="acdc_setup_done", **summary)


NO_URL = "https://thor.robots.ox.ac.uk/nightowls/python/nightowls_validation.zip"
NO_BYTES = 57481286834
NO_SHA256 = "6663dc5099714ffb8c18bb37942ce523de9dfdda44327284bdab12354e8fcf9d"  # Sol, docs/datasets/2026-11-17_nightowls_archive_verification.md
NO_ZIP = ROOT / "nightowls" / "nightowls_validation.zip"
NO_LIMIT_S = 45 * 60


def nightowls_fetch(parts=16):
    """Direct ranged download inside Colab; abort if projected >45 min; exact size + SHA-256."""
    import threading
    import urllib.request
    NO_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if NO_ZIP.exists() and NO_ZIP.stat().st_size == NO_BYTES and sha_file(NO_ZIP) == NO_SHA256:
        log(stage="nightowls_verified", cached=True)
        return
    with open(NO_ZIP, "wb") as f:
        f.truncate(NO_BYTES)
    step = -(-NO_BYTES // parts)
    done = [0] * parts
    errors = []
    stop = threading.Event()

    def worker(i):
        lo, hi = i * step, min(NO_BYTES, (i + 1) * step) - 1
        pos = lo
        for attempt in range(5):
            try:
                req = urllib.request.Request(NO_URL, headers={"Range": f"bytes={pos}-{hi}"})
                with urllib.request.urlopen(req, timeout=120) as r, open(NO_ZIP, "r+b") as f:
                    if r.status != 206:
                        raise RuntimeError(f"expected 206, got {r.status}")
                    f.seek(pos)
                    while pos <= hi and not stop.is_set():
                        chunk = r.read(8 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        pos += len(chunk)
                        done[i] = pos - lo
                if pos > hi or stop.is_set():
                    return
            except Exception as e:  # retry from current position
                errors.append(f"part {i} attempt {attempt}: {e}")
                time.sleep(5)
        errors.append(f"part {i} incomplete")

    t0 = time.time()
    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(parts)]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(30)
        el, got = time.time() - t0, sum(done)
        projected = el / max(got, 1) * NO_BYTES
        log(stage="nightowls_download", gib=round(got / 2**30, 1), s=round(el), projected_total_s=round(projected))
        if (el > 180 and projected > NO_LIMIT_S) or el > NO_LIMIT_S:
            stop.set()
            raise SystemExit(f"NightOwls download too slow: projected {projected:.0f}s > {NO_LIMIT_S}s; stopped")
    if sum(done) != NO_BYTES or errors and any("incomplete" in e for e in errors):
        raise SystemExit(f"NightOwls download incomplete: {sum(done)} bytes; {errors[-3:]}")
    t_dl = time.time() - t0
    size, digest = NO_ZIP.stat().st_size, sha_file(NO_ZIP)
    if size != NO_BYTES or digest != NO_SHA256:
        raise SystemExit(f"NightOwls size/SHA-256 mismatch: {size} {digest}")
    summary = {"status": "PASS", "bytes": size, "sha256": digest, "download_s": round(t_dl),
               "total_s": round(time.time() - t0), "parts": parts, "retries": len(errors)}
    (ROOT / "nightowls_fetch_summary.json").write_text(json.dumps(summary))
    log(stage="nightowls_verified", **summary)


def weights():
    w = ROOT / "yolo11s.pt"
    if not w.exists():
        import urllib.request
        urllib.request.urlretrieve(
            "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt", w)
    got = sha_file(w)
    assert got == CFG["training"]["init_sha256"], f"yolo11s.pt SHA-256 mismatch {got}"
    return w


def train(name, epochs, resume=False, fraction=1.0, imgsz=None, batch=None, seed=None):
    import torch
    import ultralytics
    from ultralytics import YOLO
    assert ultralytics.__version__ == CFG["training"]["framework"].split("==")[1], ultralytics.__version__
    T = CFG["training"]
    run = RUNS / name
    stats_path = run / "updates.jsonl"
    stats = {"attempted": 0, "successful": 0, "amp_skipped": 0}
    if resume and stats_path.exists():  # counters continue across resumed segments
        last = json.loads(stats_path.read_text().strip().splitlines()[-1])
        stats.update({k: last[k] for k in ("attempted", "successful", "amp_skipped")})

    def on_start(trainer):
        orig = trainer.optimizer_step

        def step():
            sc = trainer.scaler
            before = sc.get_scale() if sc.is_enabled() else None
            orig()
            after = sc.get_scale() if sc.is_enabled() else None
            stats["attempted"] += 1
            if before is None or after >= before:
                stats["successful"] += 1
            else:
                stats["amp_skipped"] += 1
        trainer.optimizer_step = step
        stats["t_start"] = time.time()
        log(stage="train_start", epochs=trainer.epochs, start_epoch=trainer.start_epoch,
            batch=trainer.batch_size, accumulate=trainer.accumulate, images=len(trainer.train_loader.dataset))

    def on_epoch_end(trainer):
        rec = {"epoch": trainer.epoch, "wall_s": round(time.time() - stats["t_start"], 1),
               "epoch_time_s": round(getattr(trainer, "epoch_time", 0) or 0, 1),
               "images_presented": len(trainer.train_loader.dataset),
               "accumulate": trainer.accumulate, "batch": trainer.batch_size,
               "attempted": stats["attempted"], "successful": stats["successful"],
               "amp_skipped": stats["amp_skipped"],
               "peak_mem_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
               "metrics": {k: round(float(v), 5) for k, v in (trainer.metrics or {}).items()}}
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        with stats_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        log(stage="epoch", **{k: v for k, v in rec.items() if k != "metrics"})

    if resume:
        model = YOLO(str(run / "weights" / "last.pt"))
    else:
        model = YOLO(str(weights()))
    model.add_callback("on_train_start", on_start)
    model.add_callback("on_fit_epoch_end", on_epoch_end)
    if resume:
        model.train(resume=True)
    else:
        model.train(data=str(DATA / "data.yaml"), epochs=epochs, imgsz=imgsz or T["imgsz"], batch=batch or T["batch"],
                    nbs=T["nbs"], optimizer=T["optimizer"], lr0=T["lr0"], seed=T["seed"] if seed is None else seed,
                    deterministic=T["deterministic"], cache=T["cache"], workers=T["workers"],
                    patience=T["patience"], amp=T["amp"], project=str(RUNS), name=name, exist_ok=True,
                    fraction=fraction, plots=False, val=True, save_period=-1)
    log(stage="train_done", **{k: v for k, v in stats.items() if k != "t_start"})


def infer(weights_path, out, imgsz=None, batch=16, image_set="bdd"):
    # Ultralytics treats a list source as ONE batch (its batch= is ignored for lists), so the chunk
    # length is the effective prediction batch. All images are 1280x720: letterbox shapes are identical.
    import numpy as np
    import ultralytics
    from ultralytics import YOLO
    assert ultralytics.__version__ == CFG["training"]["framework"].split("==")[1]
    I = CFG["inference"]
    if image_set == "bdd":
        sel = json.loads((PACKET / "manifest_selection.json").read_text())
        val = json.loads((PACKET / "manifest_val.json").read_text())
        items = [("selection", n, DATA / "images/train" / f"{n}.jpg") for n in sel]
        items += [("val", n, DATA / "images/val" / f"{n}.jpg") for n in sorted(val)]
    elif image_set == "nightcal":
        items = [("nightcal", n, DATA / "images/nightcal" / f"{n}.jpg")
                 for n in json.loads((PACKET / "manifest_nightcal.json").read_text())]
    elif image_set == "acdc":
        items = [(i["role"], i["name"], ACDC / "images" / i["name"]) for i in json.loads((ACDC / "list.json").read_text())]
    else:  # nightowls: every PNG member, decoded from the verified ZIP (no extraction); cohort filter at evaluation
        assert NO_ZIP.stat().st_size == NO_BYTES and (ROOT / "nightowls_fetch_summary.json").exists()
        with zipfile.ZipFile(NO_ZIP) as z:
            members = sorted(m for m in z.namelist() if m.lower().endswith(".png"))
        items = [("nightowls", Path(m).name, m) for m in members]
        assert len({n for _, n, _ in items}) == len(items), "duplicate NightOwls basenames"
    model = YOLO(str(weights_path))
    names, roles, offsets, totals = [], [], [0], []
    shapes = set()
    boxes, scores = [], []
    t0 = time.time()
    chunk = batch
    if image_set == "nightowls":
        import cv2
        import threading
        from concurrent.futures import ThreadPoolExecutor
        local = threading.local()

        def decode(member):
            if not hasattr(local, "z"):
                local.z = zipfile.ZipFile(NO_ZIP)
            im = cv2.imdecode(np.frombuffer(local.z.read(member), np.uint8), cv2.IMREAD_COLOR)  # = cv2.imread
            assert im is not None, member
            return im
        pool = ThreadPoolExecutor(8)
        source = lambda part: list(pool.map(decode, [p for _, _, p in part]))  # noqa: E731
    else:
        source = lambda part: [str(p) for _, _, p in part]  # noqa: E731
    for start in range(0, len(items), chunk):
        part = items[start:start + chunk]
        results = model.predict(source(part), imgsz=imgsz or I["imgsz"], conf=I["conf_floor"],
                                iou=I["nms_iou"], max_det=I["max_det_cap"], half=I["half"],
                                agnostic_nms=I["agnostic_nms"], batch=batch, verbose=False)
        for (role, n, _), r in zip(part, results):
            b = r.boxes
            cls = b.cls.cpu().numpy().astype(int)
            keep = cls == 0
            boxes.append(b.xyxy.cpu().numpy()[keep].astype(np.float32))
            scores.append(b.conf.cpu().numpy()[keep].astype(np.float32))
            names.append(n)
            roles.append(role)
            shapes.add(tuple(int(x) for x in r.orig_shape))
            totals.append(len(cls))
            offsets.append(offsets[-1] + int(keep.sum()))
        log(stage="infer", done=start + len(part), of=len(items), s=round(time.time() - t0))
    np.savez_compressed(out, names=np.array(names), roles=np.array(roles), offsets=np.array(offsets),
                        all_class_candidates=np.array(totals), boxes=np.concatenate(boxes),
                        scores=np.concatenate(scores))
    summary = {"images": len(names), "image_set": image_set, "imgsz": imgsz or I["imgsz"], "predict_batch": batch, "orig_shapes_hw": sorted(shapes), "ped_candidates": offsets[-1], "seconds": round(time.time() - t0),
               "cap_hits": int(sum(t >= I["max_det_cap"] for t in totals)),
               "weights_sha256": sha_file(weights_path), "ultralytics": ultralytics.__version__,
               "out_sha256": sha_file(out)}
    Path(str(out) + ".json").write_text(json.dumps(summary))
    log(stage="infer_done", **summary)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["setup", "acdc_setup", "nightowls_fetch", "train", "infer"])
    ap.add_argument("--set", default="bdd", choices=["bdd", "nightcal", "acdc", "nightowls"])
    ap.add_argument("--name")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--fraction", type=float, default=1.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--weights")
    ap.add_argument("--out")
    ap.add_argument("--imgsz", type=int)
    ap.add_argument("--batch", type=int)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    os.chdir(ROOT)
    if a.stage == "setup":
        setup()
    elif a.stage == "acdc_setup":
        acdc_setup()
    elif a.stage == "nightowls_fetch":
        nightowls_fetch()
    elif a.stage == "train":
        train(a.name, a.epochs, a.resume, a.fraction, a.imgsz, a.batch, a.seed)
    else:
        infer(Path(a.weights), Path(a.out), a.imgsz, a.batch or (4 if (a.imgsz or 640) > 640 else 16), a.set)
