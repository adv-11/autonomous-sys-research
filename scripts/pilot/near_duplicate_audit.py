"""Bounded perceptual near-duplicate audit of ACDC normal references (Claude, 2026-11-09).

  python -I scripts/pilot/near_duplicate_audit.py hash      --config configs/research/development_pilot.json
  python -I scripts/pilot/near_duplicate_audit.py screen    --config ...
  python -I scripts/pilot/near_duplicate_audit.py summarize --config ... --review REVIEW.json --out SUMMARY.json

``hash`` verifies the private group manifest, then decodes the 4,006 references once
(checking raw bytes against the manifest) and caches pHash/dHash privately. ``screen``
enumerates flagged pairs, writes the private review queue and contact sheets. After the
visual review, ``summarize`` writes the compact aggregate. Paths and recording tokens
stay in the private output directory; the aggregate holds counts and anonymous pair ranks.
Needs Pillow and numpy (the RT-DETRv2 venv has both); nothing is installed.

The historical snapshot has been independently reproduced. CLI reprocessing is
disabled pending cache-provenance and protected-output validation (review F8).
Pure analysis functions remain available for synthetic tests; no re-audit is needed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from threshold_transfer import near_duplicates as nd  # noqa: E402
from threshold_transfer.acdc import parse_file_name  # noqa: E402

AUDIT_REPROCESSING_HOLD = ("DISABLED: audit CLI reprocessing is on hold pending cache binding, "
                           "strict configuration and protected-output validation. "
                           "The reviewed snapshot is retained; no automatic rerun is enabled.")


def _cfg(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    return cfg, cfg["near_duplicate_audit"], REPO / cfg["private_output_dir"] / "near_duplicates"


def _write(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, allow_nan=False), encoding="utf-8")


_AUDIT = {}


def load_manifest(audit):
    _AUDIT.update(audit)
    raw = Path(audit["group_manifest"]).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != audit["group_manifest_sha256"]:
        raise SystemExit(f"group manifest hash {digest} differs from the committed summary")
    return json.loads(raw)


def _hash_one(args):
    from PIL import Image

    path, expected_sha, expected_size = args
    raw = Path(path).read_bytes()
    ok = hashlib.sha256(raw).hexdigest() == expected_sha and len(raw) == expected_size
    with Image.open(io.BytesIO(raw)) as im:
        size = im.size
        gray = im.convert("L")
    p = nd.phash_bits(_resized(gray, (nd.PHASH_SIZE, nd.PHASH_SIZE)))
    d = nd.dhash_bits(_resized(gray, (nd.DHASH_SHAPE[1], nd.DHASH_SHAPE[0])))
    return {"bytes_match_manifest": ok, "width": size[0], "height": size[1], "phash": p, "dhash": d}


def _resized(gray, wh):
    import numpy as np
    from PIL import Image

    return np.asarray(gray.resize(wh, Image.LANCZOS), dtype=np.float64)


def cmd_hash(cfg, audit, out):
    manifest = load_manifest(audit)
    rgb = Path(audit["acdc_root"]) / audit["rgb_subdir"]
    refs = [i for i in manifest["images"] if parse_file_name(i["relative_path"])["reference"]]
    if len(refs) != 4006:
        raise SystemExit(f"expected 4006 references, found {len(refs)}")
    jobs = [(str(rgb / i["relative_path"]), i["sha256"], i["size_bytes"]) for i in refs]
    with ProcessPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_hash_one, jobs, chunksize=16))
    rows = [{"path": i["relative_path"], "component": i["candidate_group_id"],
             "condition": parse_file_name(i["relative_path"])["condition"], **r}
            for i, r in zip(refs, results)]
    bad = [r["path"] for r in rows if not r["bytes_match_manifest"]]
    _write({"manifest_sha256": audit["group_manifest_sha256"], "representation": audit["representation"],
            "byte_mismatches": bad, "rows": rows}, out / "reference_hashes.json")
    print(f"hashed {len(rows)} references; byte mismatches: {len(bad)}")


def _controls(rows, manifest):
    """Positive controls: byte-identical reference groups and nearest same-chapter frames."""
    by_sha = {}
    sha = {i["relative_path"]: i["sha256"] for i in manifest["images"]}
    for r in rows:
        by_sha.setdefault(sha[r["path"]], []).append(r)
    identical = [nd.hamming(g[0]["phash"], x["phash"]) for g in by_sha.values() if len(g) > 1 for x in g[1:]]
    chapters = {}
    for r in rows:
        info = parse_file_name(r["path"])
        chapters.setdefault((info["condition"], info["sequence"]), []).append((int(info["frame"]), r))
    adjacent = []
    for frames in chapters.values():
        frames.sort(key=lambda t: t[0])
        for (fa, a), (fb, b) in zip(frames, frames[1:]):
            if sha[a["path"]] != sha[b["path"]]:
                adjacent.append(nd.hamming(a["phash"], b["phash"]))
    return {"byte_identical_reference_star_comparisons_phash_distance": sorted(identical),
            "adjacent_same_chapter_distinct_bytes_phash_distance_histogram":
                {str(d): adjacent.count(d) for d in sorted(set(adjacent))},
            "adjacent_same_chapter_pairs": len(adjacent)}


def _sheet(pairs, rgb, path):
    from PIL import Image, ImageDraw

    w, h = 800, 450
    sheet = Image.new("RGB", (2 * w + 10, len(pairs) * (h + 30)), "white")
    draw = ImageDraw.Draw(sheet)
    for k, p in enumerate(pairs):
        y = k * (h + 30)
        draw.text((5, y + 5), f"rank {p['rank']}  {p['category']}  pHash {p['phash_distance']}  "
                              f"dHash {p['dhash_distance']}  pairs {p['image_pairs_in_component_pair']}", fill="black")
        for j, key in enumerate(("a", "b")):
            with Image.open(rgb / p[key]) as im:
                sheet.paste(im.convert("RGB").resize((w, h), Image.LANCZOS), (j * (w + 10), y + 30))
    sheet.save(path)


def cmd_screen(cfg, audit, out):
    cache = json.loads((out / "reference_hashes.json").read_text(encoding="utf-8"))
    rows = cache["rows"]
    manifest = load_manifest(audit)
    t_max = max(audit["phash_thresholds"])
    pairs = nd.flagged_pairs(rows, t_max)
    queue, remaining = nd.review_queue(pairs, audit["max_visual_review_pairs"])
    for k, p in enumerate(queue + remaining, 1):
        p["rank"] = k
    hist = nd.distance_histogram([r["phash"] for r in rows], [(r["component"], r["condition"]) for r in rows])
    rgb = Path(audit["acdc_root"]) / audit["rgb_subdir"]
    sheets = out / "contact_sheets"
    sheets.mkdir(parents=True, exist_ok=True)
    for s in range(0, len(queue), 3):
        _sheet(queue[s:s + 3], rgb, sheets / f"review_{s // 3 + 1:02d}.png")
    _write({"pairs": [{**p, "components": list(p["components"]), "conditions": list(p["conditions"])}
                      for p in pairs],
            "queue": [{**p, "components": list(p["components"]), "conditions": list(p["conditions"])}
                      for p in queue],
            "remaining": [{**p, "components": list(p["components"]), "conditions": list(p["conditions"])}
                          for p in remaining],
            "histograms": hist, "controls": _controls(rows, manifest)}, out / "screen.json")
    print(json.dumps({"flag_summary": nd.summarize_flags(pairs, audit["phash_thresholds"]),
                      "queue": len(queue), "remaining": len(remaining),
                      "controls": _controls(rows, manifest)}, indent=1))


CLOSURE_PREFIX = "acdc-reference-closure-v2"


def _closure_v2(manifest, comp, cond, labelled, queue, labels, remaining, out):
    """Proposed reference-closure-v2 (coordinator-authorized CPU feasibility sensitivity).

    v1 components plus visually confirmed same-capture links only; whole closures touching an
    originally descriptive_only component are excluded. The v1 manifest is not modified, and no
    roles, seeds or folds are assigned here.
    """
    role = {i["relative_path"]: i["proposed_role"] for i in manifest["images"]}
    descriptive = [i for i, r in role.items() if r == "descriptive_only"]

    def ledger_row(p, status):
        return {"rank": p["rank"], "status": status, "components": list(p["components"]),
                "representative_a": p["a"], "representative_b": p["b"], "category": p["category"],
                "phash_distance": p["phash_distance"], "dhash_distance": p["dhash_distance"],
                "image_pairs_in_component_pair": p["image_pairs_in_component_pair"]}

    def status(p):
        lab = labels[p["rank"]]
        if lab["label"] == "confirmed_same_place":
            return "confirmed_same_capture" if lab.get("transient_match") is True else "confirmed_same_place_other_pass"
        return lab["label"]

    ledger = [ledger_row(p, status(p)) for p in queue] + [ledger_row(p, "unreviewed") for p in remaining]
    same_capture = [tuple(r["components"]) for r in ledger if r["status"] == "confirmed_same_capture"]
    pessimistic = [tuple(r["components"]) for r in ledger
                   if r["status"] not in ("rejected_different_place",)]
    variants = {"v1_primary_same_exclusion": [], "v2_confirmed_same_capture": same_capture,
                "v2_pessimistic_all_nonrejected_flags": pessimistic}
    support = {}
    for name, edges in variants.items():
        ids = nd.closure_ids(comp, edges, CLOSURE_PREFIX if name.startswith("v2_conf") else name)
        support[name] = {"links": len(edges), **nd.closure_support(ids, cond, labelled, descriptive)}
        if name == "v2_confirmed_same_capture":
            v2 = ids
    excluded = {v2[i] for i in descriptive}
    images = [{"relative_path": i["relative_path"], "v1_component": i["candidate_group_id"],
               "v1_proposed_role": i["proposed_role"], "closure_id": v2[i["relative_path"]],
               "excluded_touches_v1_descriptive_only": v2[i["relative_path"]] in excluded,
               "labelled_adverse": i["relative_path"] in set(labelled)} for i in manifest["images"]]
    closure_manifest = {"policy": CLOSURE_PREFIX, "status": "proposed sensitivity; not adopted",
                        "base_manifest_sha256": hashlib.sha256(
                            Path(_AUDIT["group_manifest"]).read_bytes()).hexdigest(),
                        "links": [{"components": list(e)} for e in same_capture], "images": images}
    raw = json.dumps(closure_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    (out / "reference_closure_v2_manifest.json").write_bytes(raw)
    ledger_raw = json.dumps({"edges": ledger}, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True).encode("ascii")
    (out / "edge_ledger.json").write_bytes(ledger_raw)
    return {"definition": "acdc-recording-v1 components plus the visually confirmed same-capture links "
                          "(transient objects coincide); content-addressed closure IDs (prefix + SHA-256 of "
                          "sorted member paths); every closure touching an originally descriptive_only v1 "
                          "component is excluded whole. Proposed sensitivity only: no roles, seeds or folds.",
            "private_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "private_edge_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
            "ledger_status_counts": dict(Counter(r["status"] for r in ledger)),
            "support": support,
            "pessimistic_note": "Treats every uncertain, same-place-other-pass and unreviewed flagged "
                                "component pair as a link; a support limit, not a confirmed merge."}


def cmd_summarize(cfg, audit, out, review_path, summary_path):
    screen = json.loads((out / "screen.json").read_text(encoding="utf-8"))
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    labels = {int(k): v for k, v in review["labels"].items()}
    queue = screen["queue"]
    if set(labels) != {p["rank"] for p in queue}:
        raise SystemExit("review must label exactly the queued ranks")
    if any(v["label"] not in nd.REVIEW_LABELS for v in labels.values()):
        raise SystemExit("unknown review label")
    manifest = load_manifest(audit)
    comp = {i["relative_path"]: i["candidate_group_id"] for i in manifest["images"]}
    cond = {p: parse_file_name(p)["condition"] for p in comp}
    labelled = [i["relative_path"] for i in manifest["images"]
                if i["detection_annotated"] and not parse_file_name(i["relative_path"])["reference"]]

    def sens(edges):
        return nd.component_sensitivity(comp, cond, labelled, edges)

    def edges_for(keep, transient=False):
        return [tuple(p["components"]) for p in queue if labels[p["rank"]]["label"] in keep
                and (not transient or labels[p["rank"]].get("transient_match") is True)]

    pairs = screen["pairs"]
    sensitivities = {
        "primary_acdc_recording_v1": sens([]),
        "plus_confirmed_same_capture": sens(edges_for({"confirmed_same_place"}, transient=True)),
        "plus_confirmed": sens(edges_for({"confirmed_same_place"})),
        "plus_confirmed_and_uncertain": sens(edges_for({"confirmed_same_place", "uncertain"})),
    }
    for t in audit["phash_thresholds"]:
        sensitivities[f"mechanical_all_cross_component_flags_le_{t}"] = sens(
            [tuple(p["components"]) for p in pairs
             if p["category"] != "within_component" and p["phash_distance"] <= t])
    roles = {i["candidate_group_id"]: i["proposed_role"] for i in manifest["images"]}
    reviewed = [{"rank": p["rank"], "category": p["category"], "phash_distance": p["phash_distance"],
                 "dhash_distance": p["dhash_distance"],
                 "image_pairs_in_component_pair": p["image_pairs_in_component_pair"],
                 "conditions": p["conditions"], "roles": sorted(roles[c] for c in p["components"]),
                 "label": labels[p["rank"]]["label"], "transient_match": labels[p["rank"]].get("transient_match"),
                 "reason": labels[p["rank"]]["reason"]}
                for p in queue]
    remaining = screen["remaining"]
    summary = {
        "author": "Claude (Opus 5.5), 2026-11-09, base 9794d81; not GPT-reviewed",
        "status": "dependency audit proposal; no primary component merged; G0 pending",
        "population": audit["population"],
        "group_manifest_sha256_verified": audit["group_manifest_sha256"],
        "representation": audit["representation"],
        "thresholds": audit["phash_thresholds"],
        "inputs_checked": {"references": 4006,
                           "byte_mismatches": len(json.loads((out / "reference_hashes.json")
                                                             .read_text(encoding="utf-8"))["byte_mismatches"])},
        "flags_by_threshold": nd.summarize_flags(pairs, audit["phash_thresholds"]),
        "phash_distance_histograms_all_pairs": screen["histograms"],
        "positive_controls": screen["controls"],
        "visual_review": {"method": review["method"], "reviewed_component_pairs": len(queue),
                          "label_counts": {k: sum(r["label"] == k for r in reviewed) for k in nd.REVIEW_LABELS},
                          "pairs": reviewed},
        "unreviewed_component_pairs": {
            "count": len(remaining),
            "closest": [{"rank": p["rank"], "category": p["category"], "phash_distance": p["phash_distance"],
                         "dhash_distance": p["dhash_distance"],
                         "image_pairs_in_component_pair": p["image_pairs_in_component_pair"]}
                        for p in sorted(remaining, key=lambda q: (q["phash_distance"], q["dhash_distance"]))[:5]],
            "by_category": {c: sum(p["category"] == c for p in remaining) for c in nd.CATEGORIES},
            "phash_distance_range": [min((p["phash_distance"] for p in remaining), default=None),
                                     max((p["phash_distance"] for p in remaining), default=None)]},
        "component_sensitivities": sensitivities,
        "interpretation_limits": [
            "Perceptual similarity is a screening flag; visual agreement shows a similar place, not the same recording, day or trip.",
            "pHash on 32x32 grayscale misses same-drive frames whose viewpoint changed; absence of a flag does not show independence.",
            "Mechanical flag sensitivities merge every flagged component pair, including unreviewed and rejected ones; they are upper-bound stress tests, not policies.",
        ],
    }
    summary["reference_closure_v2"] = _closure_v2(manifest, comp, cond, labelled, queue, labels, remaining, out)
    _write(summary, Path(summary_path))
    print(json.dumps(sensitivities, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("mode", choices=("hash", "screen", "summarize"))
    p.add_argument("--config", required=True)
    p.add_argument("--review")
    p.add_argument("--out")
    a = p.parse_args(argv)
    raise SystemExit(AUDIT_REPROCESSING_HOLD)  # before any input/output or RGB work
    cfg, audit, out = _cfg(a.config)
    if a.mode == "hash":
        return cmd_hash(cfg, audit, out)
    if a.mode == "screen":
        return cmd_screen(cfg, audit, out)
    return cmd_summarize(cfg, audit, out, a.review, a.out)


if __name__ == "__main__":
    raise SystemExit(main())
