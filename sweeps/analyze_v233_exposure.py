"""Read existing V233 engine logs only; no engine launch or economic verdict.

Continuation windows end at the next OPEX TASK or continuation. They are log
segments, not proof of additional builds versus a counterfactual trajectory.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


def fields(line):
    return dict(re.findall(r"(\w+)=([^ ]+)", line))


def analyze_score_lines(lines):
    """Join explicit line IDs, never infer a graft from cargo alone.

    Age 2 is the annual report's age, not a rolling 730-day observation.
    real_prof is vehicle operating profit; keep depreciation separate.
    """
    ready = {}
    rail = {}
    last_attempt = None
    builds = []
    revenue = defaultdict(list)
    counts = Counter()
    for number, raw in enumerate(lines, 1):
        if 'OPEX ' not in raw:
            continue
        line = raw.split('OPEX ', 1)[1].strip()
        row = fields(line)
        event = {'number': number, **row}
        if ' V252_REPLACE ' in line:
            counts['replace'] += 1
        if ' V252_ENGINE ' in line:
            counts['engine_' + row['action']] += 1
        if ' V252_SKIP ' in line:
            counts['skip_' + row['reason']] += 1
        if ' V233_SEARCH state=ready ' in line:
            ready[row['factory'], row['cargo'], row['station']] = event
        if ' RAIL_ATTEMPT ' in line:
            last_attempt = event
        if ' RAIL_BUILD ' in line:
            if last_attempt is not None and all(row.get(k) == last_attempt.get(k) for k in ('src', 'dst')):
                event['attempt'] = last_attempt
            rail[row['line']] = event
        if ' V233_BUILD factory=' in line:
            builds.append({'build': event,
                           'ready': ready.get((row['factory'], row['cargo'], row['station'])),
                           'rail': rail.get(row['line'])})
        if ' LINE_REVENUE ' in line:
            revenue[row['line']].append(event)
    for build in builds:
        reports = revenue.get(build['build']['line'], [])
        build['age2'] = next((r for r in reports if r.get('age') == '2'), None)
        build['last'] = reports[-1] if reports else None
    return {'builds': builds, 'counts': dict(counts)}


def analyze_lines(lines):
    counts = Counter()
    failures = []
    observations = defaultdict(dict)
    windows = []
    active = None
    last_attempt = None
    drops = Counter()
    for number, raw in enumerate(lines, 1):
        if "OPEX " not in raw:
            continue
        line = raw.split("OPEX ", 1)[1]
        data = fields(line)
        if " TASK name=" in line or " V233_SEARCH state=continue " in line:
            if active is not None:
                windows.append(active)
                active = None
        if " V233_SEARCH state=continue " in line:
            active = {"line": number, "rank": int(data["rank"]),
                      "built_before": int(data["built"]), "builds": [], "discards": []}
            counts["continue"] += 1
        if " V233_BUILD mode=" in line:
            counts["builds_rank_gt_zero"] += int(data["rank"]) > 0
            if active is not None:
                active["builds"].append({"line": number, **data})
        if " PROJECT_DISCARD " in line and active is not None:
            active["discards"].append({"line": number, **data})
        if " RAIL_ATTEMPT " in line:
            last_attempt = {"line": number, **data}
        if " V233_DROP " in line:
            drops[data["reason"]] += 1
            if data["reason"] == "build_failed":
                # Match the logged pair, never an unrelated preceding rail error.
                pair = data["key"].split("|")
                if last_attempt is None or [last_attempt["src"], last_attempt["dst"]] != pair[2:4]:
                    raise ValueError(f"Unmatched graft failure at line {number}")
                failures.append({"drop_line": number, "factory": data["factory"],
                                 "attempt": dict(last_attempt)})
        if " V233_GRAFT state=candidate " in line:
            counts["graft_candidates"] += 1
        if " V233_BUILD factory=" in line:
            counts["graft_built"] += 1
        if " V233_OBS " in line:
            key = (data["factory"], data["cargo"], data["station"])
            month = int(data["month"])
            if month in observations[key]:
                raise ValueError(f"Duplicate observation {key} month {month}")
            observations[key][month] = {"quantity": int(data["global_output"]),
                                       "count": int(data["count"]), "line": number}
    if active is not None:
        windows.append(active)
    examples = []
    for key, rows in observations.items():
        for month, row in sorted(rows.items()):
            counts["observations"] += 1
            counts["positive_observations"] += row["quantity"] > 0
            if row["count"] != 3 or any(m not in rows for m in (month - 1, month - 2)):
                continue
            sample = [rows[m] for m in (month - 2, month - 1, month)]
            qs = [r["quantity"] for r in sample]
            counts["full_windows"] += 1
            counts["strict_windows"] += min(qs) >= 64
            counts["mean_windows"] += sum(qs) >= 192
            if min(qs) < 64 and sum(qs) >= 192 and len(examples) < 3:
                examples.append({"factory_cargo_station": key, "month": month,
                                 "quantities": qs, "lines": [r["line"] for r in sample]})
    for window in windows:
        counts["continued_windows_with_build"] += bool(window["builds"])
        counts["continued_windows_without_build"] += not window["builds"]
        for build in window["builds"]:
            counts["continued_build_" + build["mode"]] += 1
        for discard in window["discards"]:
            counts["continued_discard_" + discard["reason"]] += 1
    return {"counts": dict(counts), "drops": dict(drops), "failures": failures,
            "mean_only_examples": examples, "windows": windows}


def analyze_directory(directory):
    variants = {}
    references = {}
    totals = Counter()
    drops = Counter()
    for path in sorted(directory.glob("*_seed*_r0.log")):
        if not path.name.startswith(("reference_", "v233expo_")):
            continue
        raw = path.read_bytes()
        result = analyze_lines(raw.decode("utf-8").splitlines())
        result.pop("windows")  # keep the review artifact compact
        result["sha256"] = hashlib.sha256(raw).hexdigest()
        if path.name.startswith("reference_"):
            references[path.name] = result
        else:
            variants[path.name] = result
            totals.update(result["counts"])
            drops.update(result["drops"])
    return {"schema": 1, "source": str(directory), "variant_totals": dict(totals),
            "variant_drops": dict(drops), "variants": variants, "references": references}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze_directory(args.directory)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
