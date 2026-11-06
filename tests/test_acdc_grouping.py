"""Synthetic tests for threshold_transfer.acdc_grouping (no ACDC data, no detector).

Several cases adapt the GPT draft's tests (incomplete; Codex credits exhausted); the
byte-identity, cross-condition, design-math and end-to-end cases are Claude additions.
"""

import copy
import hashlib
import io
import json
import random
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from threshold_transfer import acdc_grouping as G
from threshold_transfer.acdc import EXPECTED_CATEGORIES
from threshold_transfer.data import PreflightError


def name(seq="GOPR0001", frame=1, split="train", ref=False, condition="fog"):
    return (f"{condition}/{split}{'_ref' if ref else ''}/{seq}/"
            f"{seq}_frame_{frame:06d}_rgb{'_ref' if ref else ''}_anon.png")


def doc(images, annotations=()):
    return {"categories": [{"id": k, "name": v[0], "supercategory": v[1]}
                           for k, v in EXPECTED_CATEGORIES.items()],
            "images": [{"id": i, "file_name": n} for i, n in enumerate(images)],
            "annotations": list(annotations)}


FRAME = {"train": 1, "val": 2}


def n_groups(groups):
    return len(set(groups.values()))


class GraphTests(unittest.TestCase):
    def test_transitive_merging_over_chapter_recording_and_pair(self):
        # a-b share a chapter; b-c share a recording number (different chapter);
        # c-d are an adverse/reference pair. Only transitivity joins a and d.
        a, b = name(frame=1), name(frame=2, split="val")
        c, d = name("GP010001", frame=5, split="val"), name("GP010001", frame=5, split="val", ref=True)
        groups, edges, _ = G.build_components([d, c, b, a])
        self.assertEqual(n_groups(groups), 1)
        self.assertEqual({e["type"] for e in edges}, {"chapter", "pair", "recording"})
        self.assertEqual(n_groups(G.build_components([a, b, c, d], recording_links=False)[0]), 2)

    def test_pair_link_across_splits(self):
        a, b = name(split="train"), name(split="val", ref=True)
        groups, edges, parsed = G.build_components([a, b], recording_links=False)
        self.assertEqual(parsed[a]["pair_key"], parsed[b]["pair_key"])
        self.assertEqual(groups[a], groups[b])
        self.assertIn({"type": "pair", "a": a, "b": b}, edges)
        self.assertNotEqual(G.parse_name(name())["pair_key"], G.parse_name(name(frame=2))["pair_key"])

    def test_recording_number_is_global_and_distinct_numbers_stay_apart(self):
        a, b, c = name(), name(condition="night"), name("GOPR0002")
        groups = G.build_components([a, b, c])[0]
        self.assertEqual(groups[a], groups[b])
        self.assertNotEqual(groups[a], groups[c])

    def test_identical_bytes_merge_across_conditions(self):
        fog_ref, snow_ref = name("GOPR0001", ref=True), name("GOPR0009", ref=True, condition="snow")
        fog, snow = name("GOPR0001"), name("GOPR0009", condition="snow")
        paths = [fog, fog_ref, snow, snow_ref]
        content = {p: hashlib.sha256(p.encode()).hexdigest() for p in paths}
        self.assertEqual(n_groups(G.build_components(paths, content=content)[0]), 2)
        content[snow_ref] = content[fog_ref]
        groups, edges, _ = G.build_components(paths, content=content)
        self.assertEqual(n_groups(groups), 1)
        self.assertEqual([e["type"] for e in edges if e["type"] == "identical_bytes"], ["identical_bytes"])
        with self.assertRaises(PreflightError):
            G.build_components(paths, content={fog: "x"})

    def test_fail_closed_on_unknown_or_malformed_names(self):
        bad = [None, 3, [], "", name("video01"), name("GP000001"), name("GOPR001"),
               name("GX010001"), name().replace("000001", "00001"),
               name().replace("fog/", "mist/"), name().replace("train/", "dev/"),
               name().replace("rgb_anon", "rgb_ref_anon"), name().replace("/GOPR0001/", "/GOPR0002/"),
               "../" + name(), name().replace("/", "\\"), name().replace("000001", "00000١"),
               name() + ".bak", "rgb_anon/" + name()]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(PreflightError):
                G.build_components([value])
        with self.assertRaises(PreflightError):
            G.build_components([name(), None])
        with self.assertRaises(PreflightError):
            G.build_components([name(), name()])

    def test_order_determinism_of_groups_edges_and_roles(self):
        paths = [name(f"GOPR{i:04d}", split=s, ref=r, condition=c)
                 for i in range(1, 13) for s in ("train", "val") for r in (False, True)
                 for c in ("fog", "rain") if (i % 2 == 0) == (c == "fog")]
        content = {p: hashlib.sha256(p.encode()).hexdigest() for p in paths}
        original = G.build_components(paths, content=content)
        shuffled = paths[:]
        random.Random(7).shuffle(shuffled)
        self.assertEqual(original, G.build_components(shuffled, content=content))
        groups, _, parsed = original
        labelled = [p for p in paths if not parsed[p]["reference"]]
        self.assertEqual(G.allocate(groups, parsed, labelled),
                         G.allocate(groups, parsed, list(reversed(labelled))))


class AllocationTests(unittest.TestCase):
    def test_fixed_rule_and_no_component_split_across_roles(self):
        rng = random.Random(11)
        paths = set()
        for _ in range(400):
            # Disjoint number ranges per condition keep every stratum single-condition.
            condition = rng.choice(["fog", "night"])
            number = rng.randint(1, 9) + (10 if condition == "night" else 0)
            prefix = rng.choice(["GOPR", "GP01", "GP02"])
            paths.add(name(f"{prefix}{number:04d}", frame=rng.randint(1, 1000),
                           split=rng.choice(["train", "val", "test"]), condition=condition))
        paths |= {p.replace("_rgb_anon", "_rgb_ref_anon").replace(f"/{s}/", f"/{s}_ref/")
                  for p in paths for s in ("train", "val", "test") if f"/{s}/" in p}
        groups, _, parsed = G.build_components(paths)
        adverse = [p for p in paths if parsed[p]["split"] != "test" and not parsed[p]["reference"]]
        roles = G.allocate(groups, parsed, adverse)
        image_roles = {p: roles[groups[p]] for p in paths}
        for key in ("recording_number", "pair_key"):
            seen = {}
            for p in paths:
                k = (parsed[p][key],)
                self.assertEqual(seen.setdefault(k, image_roles[p]), image_roles[p])
        # Reproduce the documented rule for each single-condition stratum.
        for condition in ("fog", "night"):
            comps = sorted({groups[p] for p in adverse if parsed[p]["condition"] == condition},
                           key=lambda g: (hashlib.sha256((G.SEED + "\n" + g).encode()).hexdigest(), g))
            cut = (len(comps) + 3) // 4
            expected = [G.ROLES[0]] * cut + [G.ROLES[1]] * cut + [G.ROLES[2]] * (len(comps) - 2 * cut)
            self.assertEqual([roles[g] for g in comps], expected)

    def test_small_or_cross_condition_strata_are_descriptive_and_unlabelled_unallocated(self):
        paths = [name(f"GOPR{i:04d}") for i in range(1, 4)] + [name("GOPR0009", split="test")]
        groups, _, parsed = G.build_components(paths)
        roles = G.allocate(groups, parsed, paths[:2])
        self.assertEqual(Counter(roles.values()), {"descriptive_only": 2, "unlabelled_only": 2})
        # A component spanning two conditions forms its own signature stratum.
        mixed = [name(f"GOPR{i:04d}") for i in range(1, 5)] + [name("GOPR0001", condition="snow")]
        groups, _, parsed = G.build_components(mixed)
        roles = G.allocate(groups, parsed, mixed)
        self.assertEqual(roles[groups[mixed[0]]], "descriptive_only")
        self.assertEqual(Counter(roles[groups[p]] for p in mixed[1:4]),
                         {"calibrator_fit": 1, "threshold_selection": 1, "held_out": 1})

    def test_allocation_population_must_be_labelled_adverse(self):
        paths = [name(split="test"), name(ref=True)]
        groups, _, parsed = G.build_components(paths)
        for n in paths + [name("GOPR9999")]:
            with self.subTest(n=n), self.assertRaises(PreflightError):
                G.allocate(groups, parsed, [n])

    def test_session_proxy_chains_close_numbers_within_condition_only(self):
        paths = [name("GOPR0010"), name("GOPR0012"), name("GOPR0020"), name("GOPR0011", condition="rain")]
        groups, _, parsed = G.build_components(paths)
        self.assertEqual(G.session_proxy_count(parsed, groups, 0)["fog"], 3)
        self.assertEqual(G.session_proxy_count(parsed, groups, 2)["fog"], 2)
        self.assertEqual(G.session_proxy_count(parsed, groups, 10)["fog"], 1)
        self.assertEqual(G.session_proxy_count(parsed, groups, 10)["rain"], 1)


class CountAndDesignTests(unittest.TestCase):
    def test_annotation_counts_crowd_and_empty_definitions(self):
        paths = [name(), name(frame=2), name(frame=3)]
        anns = [{"id": i, "image_id": 0, "category_id": cid, "iscrowd": crowd}
                for i, (cid, crowd) in enumerate(((24, 0), (24, 1), (25, 0), (25, 1)))]
        anns.append({"id": 4, "image_id": 1, "category_id": 26, "iscrowd": 0})
        source = doc(paths, anns)
        before = copy.deepcopy(source)
        counts = G.annotation_counts(source, "train", False)
        summary = G.panel_summary(paths, counts, G.build_components(paths)[0])
        self.assertEqual(source, before)
        self.assertEqual([summary[k] for k in ("person_noncrowd", "person_crowd",
                                               "rider_noncrowd", "rider_crowd")], [1] * 4)
        self.assertEqual((summary["empty_images_all_classes"], summary["empty_images_noncrowd_person"],
                          summary["empty_images_noncrowd_human"]), (1, 2, 2))
        self.assertEqual(summary["largest_component_image_share"], 1)
        self.assertIsNone(G.panel_summary([], {}, {})["largest_component_image_share"])

    def test_annotation_integrity_rejection(self):
        good = doc([name()], [{"id": 0, "image_id": 0, "category_id": 24, "iscrowd": 0}])
        for key, bad in (("id", True), ("image_id", 9), ("category_id", 999),
                         ("iscrowd", True), ("iscrowd", 2)):
            changed = copy.deepcopy(good)
            changed["annotations"][0][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(PreflightError):
                G.annotation_counts(changed, "train", False)
        for section in ("images", "annotations", "categories"):
            changed = copy.deepcopy(good)
            changed[section].append(copy.deepcopy(changed[section][0]))
            with self.subTest(section=section), self.assertRaises(PreflightError):
                G.annotation_counts(changed, "train", False)
        for bad_doc in ({}, {"images": [], "annotations": [], "categories": "x"}):
            with self.assertRaises(PreflightError):
                G.annotation_counts(bad_doc, "train", False)
        with self.assertRaises(PreflightError):
            G.annotation_counts(good, "val", False)

    def test_precision_design_and_verdict(self):
        rows = G.precision_design({"two": 2, "one": 1, "many": 21})
        self.assertAlmostEqual(rows["two"]["half_width_pp"]["5"], 12.706 * 5 / 2 ** 0.5, places=2)
        self.assertIsNone(rows["one"]["half_width_pp"])
        self.assertIsNone(rows["many"]["half_width_pp"])  # outside the tabulated range
        self.assertEqual(G.feasibility_verdict({"fog": 2, "rain": 9})["verdict"],
                         "INFEASIBLE_FOR_5PP_HALF_WIDTH")
        self.assertEqual(G.feasibility_verdict({"fog": 8})["verdict"], "NOT_RULED_OUT")

    def test_chapter_continuity_detects_straddle(self):
        paths = [name("GOPR0001", 1040, "val"), name("GP010001", 3, "val"),
                 name("GOPR0002", 500, "train"), name("GP010002", 400, "train")]
        parsed = G.build_components(paths)[2]
        self.assertEqual(G.chapter_continuity(parsed),
                         {"adjacent_same_split_chapter_pairs": 2,
                          "pairs_straddling_chapter_boundary": 1, "max_frame_index": 1040})


class AuditTests(unittest.TestCase):
    # Distinct frames per split: pair keys omit the split by design.
    def make_root(self, tmp, duplicate_cross_condition=False):
        root = Path(tmp)
        for (split, ref), relative in G.AGGREGATE_FILES.items():
            paths = [name(f"GOPR{i:04d}", frame=FRAME[split], split=split, ref=ref, condition=c)
                     for i in range(1, 5) for c in ("fog", "snow") if (c == "snow") == (i > 2)]
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(doc(paths)), encoding="utf-8")
        for p in [name(f"GOPR{i:04d}", frame=FRAME[s], split=s, ref=r,
                       condition="fog" if i <= 2 else "snow")
                  for i in range(1, 5) for s in ("train", "val") for r in (False, True)]:
            image = root / G.RGB_DIR / p
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b"placeholder " + p.encode())
        if duplicate_cross_condition:
            same = b"identical normal-condition reference bytes"
            (root / G.RGB_DIR / name("GOPR0001", ref=True)).write_bytes(same)
            (root / G.RGB_DIR / name("GOPR0003", ref=True, condition="snow")).write_bytes(same)
        (root / G.README).write_text("synthetic README", encoding="utf-8")
        return root

    def test_synthetic_audit_counts_manifest_and_byte_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            summary, manifest = G.audit(root)
            self.assertEqual(summary["tree"]["images"], 16)
            self.assertEqual(summary["totals"]["adverse"]["images"], 8)
            self.assertEqual(summary["tree"]["components"], 4)
            self.assertEqual(summary["tree"]["byte_identical_file_groups"], 0)
            self.assertEqual(summary["local_full_manifest"]["sha256"],
                             hashlib.sha256(G.canonical_bytes(manifest)).hexdigest())
            self.assertEqual(G.audit(root)[0], summary)
            self.assertIsNone(G.audit(root, hash_images=False)[0]["tree"]["byte_identical_file_groups"])
        with tempfile.TemporaryDirectory() as tmp:
            summary, manifest = G.audit(self.make_root(tmp, duplicate_cross_condition=True))
            self.assertEqual(summary["tree"]["components"], 3)
            self.assertEqual(summary["tree"]["components_spanning_conditions"], 1)
            self.assertEqual(summary["tree"]["components_by_role"]["descriptive_only"], 3)
            groups = {i["candidate_group_id"] for i in manifest["images"]
                      if "GOPR0001" in i["relative_path"] or "GOPR0003" in i["relative_path"]}
            self.assertEqual(len(groups), 1)

    def test_audit_rejects_orphan_reference_and_missing_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            (root / G.AGGREGATE_FILES[("train", False)]).write_text(json.dumps(doc([])))
            with self.assertRaisesRegex(PreflightError, "orphan"):
                G.audit(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            (root / G.RGB_DIR / name("GOPR0001", ref=True)).unlink()
            with self.assertRaisesRegex(PreflightError, "one adverse and one reference"):
                G.audit(root)

    def test_cli_keeps_manifest_private_and_root_read_only(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()):
            root = self.make_root(tmp)
            for manifest, summary in ((root.parent / "leak.json", root.parent / "s.json"),
                                      (repo / "outputs/test_never_written.json", root / "s.json")):
                self.assertEqual(G.main(["--root", str(root), "--manifest", str(manifest),
                                         "--summary", str(summary)]), 2)
                self.assertFalse(summary.exists())
                self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
