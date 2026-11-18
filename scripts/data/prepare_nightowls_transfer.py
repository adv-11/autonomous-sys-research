"""GPT Sol: adapt locally available labels for the preregistered external panel.

CPU/stdlib only. No retrieval or inference. Output contains restricted dataset
records and MUST stay in gitignored data/ or outputs/. Stdout is aggregates only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from threshold_transfer.nightowls import PROFILES, SETUPS, convert_nightowls

ANNOTATION_SHA = "584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6"
PILOT_SHA = "4f31e685cd3d2d263448e7faf207d80f7befe8c6738b041c3bc4d6614b5de99a"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotations", type=Path, required=True)
    ap.add_argument("--pilot-manifest", type=Path, required=True)
    ap.add_argument("--archive", type=Path, required=True, help="index read only; CRC verified separately")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--setup", choices=SETUPS, default="reasonable")
    ap.add_argument("--profile", choices=PROFILES, required=True,
                    help="contract v2: unused_nonpedestrian is primary; person_compatible_ignore is sensitivity")
    args = ap.parse_args()
    destination = args.out.resolve()
    repo = Path(__file__).resolve().parents[2]
    if (not {"data", "outputs"}.intersection(destination.parts)
            or (destination.is_relative_to(repo) and not any(
                destination.is_relative_to(repo / private) for private in ("data", "outputs")))):
        raise ValueError("restricted output must be under data/ or outputs/")
    raw, pilot_raw = args.annotations.read_bytes(), args.pilot_manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ANNOTATION_SHA:
        raise ValueError("annotation SHA-256 differs from frozen reference")
    if hashlib.sha256(pilot_raw).hexdigest() != PILOT_SHA:
        raise ValueError("pilot exclusion manifest differs from frozen reference")
    doc, pilot = json.loads(raw), json.loads(pilot_raw)
    excluded = [i["id"] for i in pilot["images"]]
    if len(excluded) != 64 or len(set(excluded)) != 64:
        raise ValueError("exactly 64 unique pilot exclusions required")
    converted = convert_nightowls(doc, profile=args.profile, setup=args.setup,
                                 matching_category="pedestrian", exclude_image_ids=excluded,
                                 source={"sha256": ANNOTATION_SHA})
    # Check the complete native image table against archive basenames, never emit names.
    # Uniqueness prevents silently joining two directories on the same basename.
    with zipfile.ZipFile(args.archive) as z:
        names = [Path(i.filename).name for i in z.infolist() if not i.is_dir()
                 and Path(i.filename).suffix.lower() == ".png"]
    native_names = [Path(i["file_name"]).name for i in doc["images"]]
    if len(set(names)) != len(names) or len(set(native_names)) != len(native_names):
        raise ValueError("ambiguous archive/annotation image basename")
    if set(names) != set(native_names):
        raise ValueError("archive PNG coverage differs from complete annotation population")
    converted["provenance"].update(
        policy_status="preregistered before NightOwls predictions",
        policy_decision="docs/research/2026-11-17_nightowls_external_contract.md",
        pilot_exclusions_sha256=PILOT_SHA, archive_image_coverage="exact one-to-one native table")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(converted, separators=(",", ":")), encoding="utf-8")
    summary = dict(converted["provenance"]["summary"])
    summary.update(setup=args.setup, profile=args.profile, archive_native_image_coverage=True)
    groups = {i["image_id"]: i["group_id"] for i in converted["images"]}
    summary["eligible_unkeyed_gt"] = sum(not a["ignore"] and groups[a["image_id"]] is None
                                        for a in converted["annotations"])
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
