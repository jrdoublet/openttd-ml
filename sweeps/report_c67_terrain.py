"""C67.3 report: per-size dispersion and the pre-registered granularity rule.

Reads one or more `bench_c67_terrain.py` result JSONs. Rule (contract section 8):
drop a side with any invalid pair; among the rest, compare cold localized-request
opcodes by the median of paired relative deltas (S5 - S10) / S10, then memory.
S=5 is kept provisionally if that median is <= +10 %, otherwise S=10.
This is a technical design choice, not evidence of an economic gain.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

S5_MAX_EXTRA = 0.10


def spread(values: list) -> dict | None:
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {"n": len(values), "median": statistics.median(values),
            "min": min(values), "max": max(values)}


def load_pairs(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    pairs, campaigns = [], []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest, summary = data["manifest"], data["summary"]
        campaigns.append({"file": str(path), "sizes": manifest["sizes"],
                          "scan_tiles": manifest.get("scan_tiles", 0),
                          "days": manifest["days"],
                          "expected_runs": summary["expected_runs"],
                          "process_records": summary["process_records"],
                          "complete": summary["complete"],
                          "source_hashes": manifest["source_hashes"]})
        for pair in summary["pairs"]:
            pairs.append(dict(pair, scan_tiles=manifest.get("scan_tiles", 0)))
    return pairs, campaigns


def phase(pair: dict, name: str, key: str):
    return (pair.get(name) or {}).get(key)


def report(pairs: list[dict], campaigns: list[dict]) -> dict:
    sizes = sorted({p["size"] for p in pairs})
    per_size = {}
    for size in sizes:
        entry = {}
        for side in (5, 10):
            group = [p for p in pairs if p["size"] == size and p["side"] == side]
            valid = [p for p in group if p["valid"]]
            scans = [p.get("scan") or {} for p in valid]
            entry[str(side)] = {
                "pairs": len(group), "valid_pairs": len(valid),
                "cold_ops": spread([phase(p, "cold", "ops") for p in valid]),
                "cold_ticks": spread([phase(p, "cold", "ticks") for p in valid]),
                "cold_reads": spread([phase(p, "cold", "reads") for p in valid]),
                "warm_ops": spread([phase(p, "warm", "ops") for p in valid]),
                "scan_ops": spread([s.get("ops") for s in scans]),
                "scan_ops_per_read": spread([s["ops"] / s["reads"] for s in scans
                                             if s.get("ops") is not None and s.get("reads")]),
                "scan_coverage": spread([s["blocks"] / s["total"] for s in scans
                                         if s.get("blocks") is not None and s.get("total")]),
                "scan_limited": sorted({s.get("limited") for s in scans}),
                "tranche_max": max((phase(p, n, "max") or 0 for p in valid
                                    for n in ("cold", "warm", "scan")), default=None),
                "resident_max": max((s.get("resident") or 0 for s in scans), default=None),
                "peak_rss_delta_kib": spread([p["peak_rss_delta_kib"] for p in valid]),
            }
        per_size[str(size)] = entry
    matched = {}
    for p in pairs:
        matched.setdefault((p["size"], p["seed"], p["repeat"]), {})[p["side"]] = p
    deltas, by_size = [], {}
    for (size, _seed, _repeat), sides in sorted(matched.items()):
        five, ten = sides.get(5), sides.get(10)
        if not (five and ten and five["valid"] and ten["valid"]):
            continue
        a, b = phase(five, "cold", "ops"), phase(ten, "cold", "ops")
        if a is None or not b:
            continue
        deltas.append((a - b) / b)
        by_size.setdefault(str(size), []).append((a - b) / b)
    eliminated = [side for side in (5, 10)
                  if any(not p["valid"] for p in pairs if p["side"] == side)]
    all_complete = all(c["complete"] for c in campaigns)
    if not all_complete:
        choice, reason = None, "campaign incomplete: no granularity choice"
    elif set(eliminated) == {5, 10}:
        choice, reason = None, "both sides fail bounds or exactness"
    elif eliminated:
        choice = 10 if 5 in eliminated else 5
        reason = f"S={eliminated[0]} eliminated by an invalid pair"
    elif not deltas:
        choice, reason = None, "no paired cold measurement"
    else:
        median = statistics.median(deltas)
        choice = 5 if median <= S5_MAX_EXTRA else 10
        reason = f"median paired cold-ops delta S5 vs S10 = {median:+.1%}"
    return {"campaigns": campaigns, "per_size": per_size,
            "cold_ops_rel_delta_s5_vs_s10": {
                "pooled": spread(deltas),
                "by_size": {k: spread(v) for k, v in by_size.items()}},
            "eliminated_sides": eliminated, "choice": choice, "reason": reason}


def selftest():
    def pair(size, seed, side, ops, valid=True):
        return {"size": size, "seed": seed, "repeat": 0, "side": side, "valid": valid,
                "peak_rss_delta_kib": 8000, "cold": {"ops": ops, "max": 1200},
                "warm": {"ops": 10}, "scan": {"ops": 100, "reads": 10, "blocks": 4,
                                              "total": 4, "limited": 0, "resident": 4}}
    camp = [{"complete": True}]
    out = report([pair(8, 1, 5, 100), pair(8, 1, 10, 400)], camp)
    assert out["choice"] == 5 and out["cold_ops_rel_delta_s5_vs_s10"]["pooled"]["median"] == -0.75
    out = report([pair(8, 1, 5, 500), pair(8, 1, 10, 400)], camp)
    assert out["choice"] == 10
    out = report([pair(8, 1, 5, 100, valid=False), pair(8, 1, 10, 400)], camp)
    assert out["choice"] == 10 and out["eliminated_sides"] == [5]
    out = report([pair(8, 1, 5, 100), pair(8, 1, 10, 400)], [{"complete": False}])
    assert out["choice"] is None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="*", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        print("C67 report selftest OK")
        return
    if not args.results:
        parser.error("give at least one result JSON")
    pairs, campaigns = load_pairs(args.results)
    out = report(pairs, campaigns)
    text = json.dumps(out, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
