#!/usr/bin/env python3
"""V308: compare cinq motifs de sondage 8x8 a la verite exhaustive.

Usage: python sweeps/diag_v308_carto.py results/<campaign>_engine [--json out.json]
Les comptes de rivieres vus sont un indice de detection, pas une reconstruction de
leur connexite: seul le balayage des 64 tuiles etablit une riviere traversante.
"""

import argparse
import gzip
import json
import re
import statistics
from pathlib import Path


ARM_NAMES = ("v307", "full6", "short6", "parity6", "flatdry6")
CLASSES = ("sea", "lake", "river", "coast", "house", "town", "city", "obst", "mountain", "river_cross")
PATTERN = re.compile(r"\bV308_BLOCK\s+(.*)$")


def parse_fields(payload):
    fields = {}
    for part in payload.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        try:
            fields[key] = int(value)
        except ValueError:
            fields[key] = value
    return fields


def logs(paths):
    for path in paths:
        path = Path(path)
        if path.is_dir():
            yield from sorted(path.rglob("*.log"))
            yield from sorted(path.rglob("*.log.gz"))
        elif path.is_file():
            yield path


def read_blocks(paths):
    for path in logs(paths):
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                match = PATTERN.search(line)
                if match:
                    fields = parse_fields(match.group(1))
                    if all(k + "_ops" in fields for k in ARM_NAMES) and "t_sea" in fields:
                        fields["source"] = str(path)
                        yield fields


def is_present(record, prefix, kind):
    if kind == "mountain":
        return record.get(prefix + "_relief", 0) >= 4
    if kind == "city":
        return record.get(prefix + "_house", 0) >= 2 or record.get(prefix + "_town", 0) >= 3
    if kind == "river_cross":
        return record.get(prefix + ("_river_cross" if prefix == "t" else "_river"), 0) > 0
    return record.get(prefix + "_" + kind, 0) > 0


def percentile(values, percent):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * percent / 100
    lo = int(position)
    hi = min(lo + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (position - lo), 1)


def summarize(blocks):
    rows = []
    for name in ARM_NAMES:
        ops = [b[name + "_ops"] for b in blocks]
        classes = {}
        for kind in CLASSES:
            truth = [is_present(b, "t", kind) for b in blocks]
            seen = [is_present(b, name, kind) for b in blocks]
            positives = sum(truth)
            negatives = len(truth) - positives
            missed = sum(t and not s for t, s in zip(truth, seen))
            false = sum(not t and s for t, s in zip(truth, seen))
            classes[kind] = {
                "truth": positives, "missed": missed,
                "miss_pct": round(100 * missed / positives, 1) if positives else None,
                "false_pos": false,
                "false_pct": round(100 * false / negatives, 1) if negatives else None,
            }
        rows.append({
            "motif": name, "n": len(blocks), "ops_median": statistics.median(ops) if ops else None,
            "ops_p90": percentile(ops, 90), "classes": classes,
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Dossiers de campagne ou journaux")
    parser.add_argument("--json", type=Path, help="Exporter un tableau machine")
    args = parser.parse_args()
    blocks = list(read_blocks(args.paths))
    rows = summarize(blocks)
    print(f"V308: {len(blocks)} blocs complets (5 bras + verite)")
    for row in rows:
        print(f"{row['motif']:9s} ops median={row['ops_median']} p90={row['ops_p90']}")
        for kind, fields in row["classes"].items():
            print(f"  {kind:12s} truth={fields['truth']:4d} missed={fields['missed']:4d} "
                  f"miss%={fields['miss_pct']} fp={fields['false_pos']:4d} fp%={fields['false_pct']}")
    if args.json:
        args.json.write_text(json.dumps({"blocks": len(blocks), "rows": rows}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
