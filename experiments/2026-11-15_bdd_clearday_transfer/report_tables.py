"""Claude Opus: markdown tables from aggregate evaluation JSON (no per-image data).

    python report_tables.py ARM=eval.json:target [...]
"""
from __future__ import annotations

import json
import sys

ROWS = [("val:clear_day", "clear day"), ("val:cloudy_day", "cloudy day"), ("val:rainy_day", "rain (day)"),
        ("val:snowy_day", "snow (day)"), ("val:dawn_dusk", "dawn/dusk"), ("val:night", "night"),
        ("val2:night_clear", "night, clear weather")]  # fog (5 images, 2 pedestrians) is reported in text only


def f(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def rng(c, d=3):
    return "" if not c else f" [{c[0]:.{d}f}, {c[1]:.{d}f}]"


def table(label, ev, target):
    s = ev["selection"][target]
    out = [f"**{label}** — {ev['population']}; target recall {target}; "
           f"t* = {f(s['threshold'], 4)}{rng(s['threshold_ci'], 4)}; selection recall {f(s['point']['recall'])}, "
           f"FPPI {f(s['point']['fppi'], 2)}, selection ceiling {f(s['selection_ceiling']['recall'])}", "",
           "| condition | images | peds | recall at t* | FPPI at t* | precision | ceiling | loss vs clear day | ceiling part | threshold part | oracle FPPI |",
           "|---|---:|---:|---|---|---:|---:|---:|---|---|---:|"]
    tr = ev["transfer"][target]
    for key, name in ROWS:
        if key not in tr:
            continue
        e, st = tr[key], ev["strata"][key]
        L, C = e.get("loss_vs_clear_day", {}), e.get("loss_ci", {})
        lv = lambda k: L[k]["value"] if k in L else None  # noqa: E731
        ce = "—" if key == "val:clear_day" else f"{f(lv('ceiling_difference'))}{rng(C.get('ceiling_difference'))}"
        th = "—" if key == "val:clear_day" else f"{f(lv('threshold_miss_difference'))}{rng(C.get('threshold_miss_difference'))}"
        lo = "—" if key == "val:clear_day" else f"{f(lv('held_out_loss'))}"
        out.append(f"| {name} | {st['images']} | {st['pedestrians']} | {f(e['operating']['recall'])}{rng(e['recall_ci'])} | "
                   f"{f(e['operating']['fppi'], 2)}{rng(e['fppi_ci'], 2)} | {f(e['operating']['precision'])} | "
                   f"{f(e['ceiling_recall'])} | {lo} | {ce} | {th} | "
                   f"{f(e['oracle']['fppi'], 2) if e['oracle']['fppi'] is not None else 'infeasible'} |")
    return "\n".join(out)


def _main():  # noqa: D103
    for arg in sys.argv[1:]:
        label, rest = arg.split("=", 1)
        path, target = rest.rsplit(":", 1)
        ev = json.load(open(path))
        if ev["transfer"][target].get("status"):
            print(f"**{label}** target {target}: {ev['transfer'][target]['status']} "
                  f"(selection ceiling {f(ev['selection'][target]['selection_ceiling']['recall'])})\n")
            continue
        print(table(label, ev, target) + "\n")


def matched_table(path):
    """Amendment 3 matched-FPPI table: night vs clear day per arm and level, plus paired differences."""
    m = json.load(open(path))
    out = [f"Population: {m['population']}.", "",
           "| arm | clear-day FPPI level | t* | clear-day recall | night recall | night FPPI | night loss | never a candidate | removed by threshold | night oracle recall at same FPPI |",
           "|---|---:|---:|---:|---|---:|---:|---|---|---:|"]
    for arm, levels in m["arms"].items():
        for L, r in levels.items():
            n, c = r["conditions"]["val:night"], r["conditions"]["val:clear_day"]
            out.append(f"| {arm} | {L} | {f(r['threshold'], 4)} | {f(c['recall'])} | {f(n['recall'])}{rng(n['recall_ci'])} | "
                       f"{f(n['fppi'], 2)} | {f(n['loss'])} | {f(n['ceiling_part'])}{rng(n['ceiling_part_ci'])} | "
                       f"{f(n['threshold_part'])}{rng(n['threshold_part_ci'])} | {f(n['oracle_same_fppi']['recall'])} |")
    out += ["", "| paired difference (night) | level | recall | loss | never a candidate | removed by threshold |",
            "|---|---:|---|---|---|---|"]
    for pair, levels in m["paired_differences"].items():
        for L, d in levels.items():
            e = d["val:night"]
            out.append(f"| {pair} | {L} | " + " | ".join(f"{e[k]['value']:+.3f}{rng(e[k]['ci'])}"
                       for k in ("recall", "loss", "ceiling_part", "threshold_part")) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    if sys.argv[1] == "--matched":
        print(matched_table(sys.argv[2]))
    else:
        _main()
