#!/usr/bin/env python3
"""Inspect single-bundle C66 diagnostic: AIR reject reasons, P2 and active services.

Events are probe-dependent and NOT full population of decisions. Line telemetry
counts active services inferred from orders, never construction events.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

LOG = re.compile(r"\bOPEX\s+(\d{4})-(\d{1,2})-\d{1,2}\s+([A-Z][A-Z0-9_]+)\s*(.*)")
KV = re.compile(r"([a-zA-Z_]+)=([^\s]+)")


def parse_log(lines):
    years = defaultdict(lambda: {"events": Counter(), "select_reject": Counter(),
                                 "reject_unique_pair_month": defaultdict(set),
                                 "project_discard": Counter(), "p2_passes": 0,
                                 "p2_start_empty": 0, "p2_with_progress": 0,
                                 "by_month": defaultdict(Counter)})
    for raw in lines:
        match = LOG.search(raw)
        if match is None:
            continue
        year, month, kind, body = match.groups()
        data = dict(KV.findall(body))
        item = years[year]
        item["events"][kind] += 1
        if kind == "SELECT_REJECT":
            reason = data.get("reason", "unknown")
            item["select_reject"][reason] += 1
            item["by_month"][str(int(month))][f"reject_{reason}"] += 1
            item["reject_unique_pair_month"][reason].add((month, data.get("pair"), data.get("type")))
        elif kind == "PROJECT_DISCARD":
            item["project_discard"][data.get("reason", "unknown")] += 1
        elif kind == "P2_PASS":
            item["p2_passes"] += 1
            item["p2_start_empty"] += data.get("in_best") == "0"
            item["p2_with_progress"] += data.get("n_built", "0") != "0"
            item["by_month"][str(int(month))]["p2_passes"] += 1
    return {year: {"events": dict(v["events"]),
                   "select_reject": dict(v["select_reject"]),
                   "reject_unique_pair_month": {reason: len(keys) for reason, keys in v["reject_unique_pair_month"].items()},
                   "project_discard": dict(v["project_discard"]),
                   "p2_passes": v["p2_passes"], "p2_start_empty": v["p2_start_empty"],
                   "p2_with_progress": v["p2_with_progress"],
                   "by_month": {m: dict(counts) for m, counts in sorted(v["by_month"].items(), key=lambda x: int(x[0]))}}
            for year, v in sorted(years.items())}


def active_services(c66, seeds):
    tel = c66.get("line_telemetry")
    if not isinstance(tel, dict) or not isinstance(tel.get("snapshots"), list):
        raise ValueError("line telemetry not collected")
    result = defaultdict(dict)
    for snap in tel["snapshots"]:
        if snap.get("seed") not in seeds or snap.get("repeat") != 0:
            continue
        arm = snap.get("arm")
        if arm not in ("OpexAI", "AAAHogEx"):
            continue
        if not snap.get("ok") or snap.get("unresolved_vehicles"):
            raise ValueError("invalid/unresolved line telemetry: " + str((snap.get("seed"), snap.get("year"), arm)))
        year = str(snap["year"])
        modes = Counter(line.get("mode", "unknown") for line in snap.get("lines", []))
        key = (str(snap["seed"]), year)
        if arm in result[key]:
            raise ValueError("duplicate services snapshot " + str((key, arm)))
        result[key][arm] = dict(modes)
    return {f"{seed}/{year}": {"opex": result[(str(seed), str(year))].get("OpexAI"),
                               "aaa": result[(str(seed), str(year))].get("AAAHogEx")}
            for seed in seeds for year in (1970, 1971, 1972, 1973, 1974)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("c66", type=Path)
    parser.add_argument("engine_logs", type=Path)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 100, 999])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    c66 = json.loads(args.c66.read_text(encoding="utf8"))
    if c66.get("failed_runs"):
        raise ValueError("unhealthy campaign")
    per_seed = {}
    for seed in args.seeds:
        files = list(args.engine_logs.glob(f"*seed{seed}_r0.log"))
        if len(files) != 1:
            raise ValueError(f"seed {seed}: exactly 1 engine log required")
        with files[0].open(encoding="utf8", errors="replace") as source:
            per_seed[str(seed)] = parse_log(source)
    report = {"source_bundle_sha256": c66.get("source_bundle_sha256"),
              "campaign": c66.get("campaign_id"), "by_seed_probe": per_seed,
              "paired_active_services": active_services(c66, args.seeds),
              "limitations": [
                  "SELECT_REJECT records each scanned rejection; repeated candidates and selections multiply counts, so neither attempts nor lost construction opportunities.",
                  "PROJECT_DISCARD may be sampled only on the monthly decision-log trigger; absence is not proof of no failures.",
                  "P2_PASS reports end-of-dispatch delta, not constructibility or actual attempts per mode.",
                  "Line telemetry reconstructs services with primary vehicles/orders and cannot show gross constructions, scrapped lines or profitability by project.",
                  "The source bundle has intrusive probes and may not reproduce the uninstrumented reference trajectory."]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    for seed in args.seeds:
        print("seed", seed)
        for y in ("1971", "1972", "1973"):
            row = per_seed[str(seed)].get(y, {})
            services = report["paired_active_services"].get(f"{seed}/{y}")
            print(" ", y, "P2", row.get("p2_passes"), "empty", row.get("p2_start_empty"),
                  "rejected", row.get("select_reject"), "services", services)


if __name__ == "__main__":
    main()
