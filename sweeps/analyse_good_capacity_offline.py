"""Read-only GOOD rail-capacity exposure, not a causal gain or a new game probe.

Links existing LINE_REVENUE reports to V284 events by (game file, line ID).
The yearly waiting snapshot is *not* an annual transport flow; the presence of
an eligible line says nothing about passing-loop constructibility or marginal ROI.
"""

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


EVENT = re.compile(r"\bOPEX (\d{4})-\d{1,2}-\d{1,2} (LINE_REVENUE|V284) (.*)$")
PAIR = re.compile(r"(?<!\S)(\w+)=([^\s]+)")


def read_logs(paths):
    lines = {}
    actions = defaultdict(list)
    files = []
    for arg in paths:
        source = Path(arg)
        files.extend(sorted(source.glob("*.log*")) if source.is_dir() else [source])
    for file in files:
        if file.suffix not in (".log", ".gz"):
            continue
        opener = gzip.open if file.suffix == ".gz" else open
        with opener(file, "rt", encoding="utf-8", errors="strict") as stream:
            for record in stream:
                match = EVENT.search(record)
                if not match:
                    continue
                date_year, kind, payload = match.groups()
                fields = dict(PAIR.findall(payload))
                if "line" not in fields:
                    continue
                try:
                    line_id = int(fields["line"])
                except ValueError:
                    continue
                key = (file.name, line_id)
                if kind == "V284":
                    actions[key].append({"year": int(date_year),
                                         "action": fields.get("action", "unknown"),
                                         "kind": fields.get("kind", "unknown"),
                                         "reason": fields.get("reason", "unknown")})
                    continue
                if (fields.get("mode"), fields.get("kind"), fields.get("cargo")) != (
                        "rail", "freight", "GOOD"):
                    continue
                needed = ("age", "wait_a", "cap", "real_prof", "vehs", "src_prod")
                if any(key_name not in fields for key_name in needed):
                    continue
                try:
                    values = {name: int(fields[name]) for name in needed}
                    year = int(fields.get("year", date_year))
                except ValueError:
                    continue
                lines[(file.name, line_id, year)] = {
                    "file": file.name, "line": line_id, "year": year, **values
                }
    return list(lines.values()), actions


def summarize(records, actions, year=1979):
    complete = [r for r in records if r["year"] == year and r["age"] >= 2
                and r["cap"] > 0 and r["wait_a"] >= 0]
    history = {(r["file"], r["line"]) for r in complete}
    events = [event for key in history for event in actions.get(key, [])
              if event["year"] <= year]
    overview = Counter()
    for record in complete:
        overview["mature_lines"] += 1
        overview["positive_profit"] += record["real_prof"] > 0
        overview["real_profit_sum"] += record["real_prof"]
        overview["wait_ge_capacity"] += record["wait_a"] >= record["cap"]
        overview["wait_ge_3_capacity"] += record["wait_a"] >= 3 * record["cap"]
        overview["wait_ge_5_capacity"] += record["wait_a"] >= 5 * record["cap"]
        overview["profit_positive_wait_ge_capacity"] += (
            record["real_prof"] > 0 and record["wait_a"] >= record["cap"])
    for e in events:
        overview[f"v284_{e['action']}_{e['kind']}" if e["action"] in ("pick", "done")
                 else f"v284_{e['action']}_{e['reason']}"] += 1
    by_seed = []
    for file in sorted({r["file"] for r in complete}):
        selected = [r for r in complete if r["file"] == file]
        by_seed.append({"file": file, "lines": len(selected),
                        "profit_sum": sum(r["real_prof"] for r in selected),
                        "wait_ge_capacity": sum(r["wait_a"] >= r["cap"] for r in selected)})
    return {"year": year, "coverage": "only LINE_REVENUE GOOD reports for mature lines",
            "overview": dict(overview), "by_seed": by_seed,
            "lines": sorted(complete, key=lambda r: (r["file"], r["line"])),
            "note": "V284 events can repeat across years; waiting snapshot is not annual cargo flow"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--year", type=int, default=1979)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    records, actions = read_logs(args.paths)
    result = summarize(records, actions, args.year)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"GOOD capacity | year={args.year} | {result['overview']}")
        print("YEARLY LINE SNAPSHOT ONLY; no annual queue-flow, ROI or qualified profit uplift")
        for item in result["by_seed"]:
            print(f"  {item['file']}: lines={item['lines']} wait>=cap="
                  f"{item['wait_ge_capacity']} profit_sum={item['profit_sum']}")


if __name__ == "__main__":
    main()
