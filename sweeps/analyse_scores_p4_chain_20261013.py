#!/usr/bin/env python3
"""P4: facteur C70 -> tête C77 -> tentative -> outcome -> ligne -> revenu.

Lecture des journaux de la campagne P4_CHAIN, jamais des parties d'autres
bundles. Un score basculé est un contre-factuel LOCAL : il ne prouve pas
que l'autre projet aurait été construit, ni un profit réseau causal.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re

FIELDS = re.compile(r"([a-zA-Z_][a-zA-Z_0-9]*)=([^ ]+)")
EVENTS = ("P4_FLIP_HEAD", "P4_FLIP_ATTEMPT", "P4_FLIP_OUTCOME",
          "P4_FLIP_RESUME", "P4_FLIP_SUMMARY", "P4_FLIP_FACTOR",
          "PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD",
          "LINE_REVENUE", "C121_BUILD", "[FLEET_PROJECT]")
OPEX_DATE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) ")
NAME = re.compile(r"^(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<rep>\d+)\.log$")


def ev(line):
    if "[0] [I]" not in line:
        return None
    for name in EVENTS:
        i = line.find(name + " ")
        if i >= 0:
            return name.strip("[]"), dict(FIELDS.findall(line[i + len(name) + 1:])), i
    return None


def safeint(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def analyse_one(path):
    heads, attempts, outcomes, resumes = {}, {}, {}, defaultdict(list)
    choices, builds, fleet, revenues, factors, summaries = [], [], [], [], [], []
    issues = []
    sim_date = None
    with path.open(encoding="utf8", errors="replace") as f:
        for index, line in enumerate(f):
            dt = OPEX_DATE.search(line)
            if dt and "[0] [I]" in line:
                sim_date = "-".join([dt[1], dt[2].zfill(2), dt[3].zfill(2)])
            item = ev(line)
            if item is None:
                continue
            name, payload, _ = item
            row = dict(payload, log_index=index, date=sim_date)
            if name == "P4_FLIP_HEAD":
                k = safeint(row.get("id"))
                if k in heads:
                    issues.append(f"head duplicate id {k}")
                heads[k] = row
            elif name == "P4_FLIP_ATTEMPT":
                k = safeint(row.get("id"))
                if k in attempts:
                    issues.append(f"attempt duplicate id {k}")
                attempts[k] = row
            elif name == "P4_FLIP_OUTCOME":
                k = safeint(row.get("id"))
                if k in outcomes:
                    issues.append(f"outcome duplicate id {k}")
                outcomes[k] = row
            elif name == "P4_FLIP_RESUME":
                resumes[safeint(row.get("id"))].append(row)
            elif name == "PROJECT_CHOSEN":
                choices.append(row)
            elif name in ("AIR_BUILD", "RAIL_BUILD", "C121_BUILD"):
                row["marker"] = name
                builds.append(row)
            elif name == "FLEET_PROJECT":
                fleet.append(row)
            elif name == "LINE_REVENUE":
                revenues.append(row)
            elif name == "P4_FLIP_FACTOR":
                factors.append(row)
            elif name == "P4_FLIP_SUMMARY":
                summaries.append(row)
    revenues_by_line = defaultdict(list)
    for rev in revenues:
        revenues_by_line[safeint(rev.get("line"))].append(rev)
    fleet_by_line = defaultdict(list)
    for e in fleet:
        fleet_by_line[safeint(e.get("line"))].append(e)
    builds_by_line = defaultdict(list)
    for b in builds:
        builds_by_line[safeint(b.get("line"))].append(b)
    episodes = []
    for k, head in sorted(heads.items()):
        a, o = attempts.get(k), outcomes.get(k)
        if a is not None and a["log_index"] <= head["log_index"]:
            issues.append(f"attempt before head {k}")
        if o is not None and (a is None or o["log_index"] <= a["log_index"]):
            issues.append(f"outcome without earlier attempt {k}")
        if a is not None and o is None:
            issues.append(f"unresolved direct constructor result {k}")
        if a is None and o is not None:
            issues.append(f"outcome without attempt {k}")
        line = safeint(o.get("new_line")) if o is not None else -1
        resumed = resumes.get(k, [])
        if o is not None and o.get("outcome") == "pending" and resumed:
            final = resumed[-1]
            if final.get("outcome") == "built":
                line = safeint(final.get("new_line"))
        if o is not None and o.get("outcome") == "built" and line < 0:
            # Fleet extension could be successful without a new line.
            if (a or {}).get("project", "").split("/")[0] != "fleet":
                issues.append(f"built without new line id {k}")
        related_builds = builds_by_line.get(line, []) if line >= 0 else []
        # Builder logs can occur before OUTCOME, never treat nearby unrelated
        # C121_BUILD as a verified lineage.
        endpoint = resumed[-1]["log_index"] if resumed else (
            o["log_index"] if o is not None else -1)
        related_builds = [b for b in related_builds if o is not None
                          and head["log_index"] <= b["log_index"] <= endpoint]
        direct = [b for b in related_builds if b["marker"] in ("AIR_BUILD", "RAIL_BUILD")]
        actual_mode = (a or {}).get("project", "").split("/")[0]
        expected_marker = {"air": "AIR_BUILD", "rail": "RAIL_BUILD"}.get(actual_mode)
        completed = bool(o is not None and (o.get("outcome") == "built"
                         or (o.get("outcome") == "pending" and resumed
                             and resumed[-1].get("outcome") == "built")))
        confirmed_build = bool(completed and (expected_marker is None or any(
            b["marker"] == expected_marker for b in direct)))
        if completed and not confirmed_build:
            issues.append(f"builder result built, but no matching {expected_marker}: id {k}")
        episodes.append({
            "id": k, "year": head.get("year"), "month": head.get("month"),
            "tier": head.get("tier"), "legacy": head.get("legacy"),
            "stable": head.get("stable"),
            "actual_mode": actual_mode, "chosen": a is not None,
            "outcome": o.get("outcome") if o else None, "new_line": line,
            "resumable": [r.get("outcome") for r in resumed],
            "direct_builder_confirmed": confirmed_build,
            "builders": related_builds,
            "revenue": revenues_by_line.get(line, []) if confirmed_build else [],
            "fleet_events": fleet_by_line.get(line, []) if confirmed_build else [],
        })
    for k in attempts:
        if k not in heads:
            issues.append(f"unmatched attempt {k}")
    counts = Counter({"heads": len(heads), "attempts": len(attempts),
                      "outcomes": len(outcomes), "resumable_events": sum(
                          len(x) for x in resumes.values()),
                      "confirmed_completed_builds": sum(x["direct_builder_confirmed"] for x in episodes),
                      "confirmed_resumed_rail_builds": sum(
                          x["direct_builder_confirmed"] and x["outcome"] == "pending"
                          for x in episodes),
                      "matured_built_with_revenue": sum(any(
                          safeint(r.get("age")) >= 2 for r in x["revenue"]) for x in episodes)})
    counts.update({f"outcome_{key}": n for key, n in Counter(
        x["outcome"] for x in episodes).items()})
    return {
        "path": str(path), "counts": dict(counts), "issues": issues,
        "reported_selects": sum(safeint(x.get("selects"), 0) for x in summaries),
        "reported_verified": sum(safeint(x.get("verified"), 0) for x in summaries),
        "reported_mismatches": sum(safeint(x.get("mismatch"), 0) for x in summaries),
        "factors": factors, "episodes": episodes,
        "limitations": [
            "The head rank is a local C77 same-budget counterfactual, not independent A/B game.",
            "A pending rail build may complete after another portfolio pass; correlate RESUME, never count pending as built.",
            "LINE_REVENUE measures line profits not C121 network externalities, and only reports observed lines.",
            "All diagnostic runs have extra opcodes; their money/annual profits cannot qualify policy adoption.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    games = {}
    for path in sorted(args.engine_dir.glob("*.log")):
        match = NAME.fullmatch(path.name)
        if match is None:
            continue
        key = f"{match['policy']}:s{match['seed']}:r{match['rep']}"
        games[key] = analyse_one(path)
    if not games:
        raise SystemExit("no valid logs")
    summary = {
        "games": games, "total": {
            k: sum(d["counts"].get(k, 0) for d in games.values())
            for k in set().union(*(d["counts"] for d in games.values()))
        },
        "issues": {k: v["issues"] for k, v in games.items() if v["issues"]},
        "provenance": "one isolated P4_CHAIN bundle, paired game seeds, probe ON both arms",
        "calibration_ready": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("games", len(games), "totals", json.dumps(summary["total"]))
    for k, d in games.items():
        print(k, d["counts"], "problems", d["issues"][:3])
    print("output", args.out)
    if summary["issues"]:
        print("CAUTION: unresolved joins; see JSON. Never silently infer builds.")


if __name__ == "__main__":
    main()
