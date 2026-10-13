"""Diagnostic d'exposition P3 : comparer les mêmes portefeuilles éligibles C77.

Les décomptes sont des élections, pas des occasions indépendantes d'achat.
L'absence de flip dans une graine n'est pas une preuve de neutralité économique.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import re


SUMMARY = re.compile(r"\bP3_PORTFOLIO (.+)$")
CANDIDATE = re.compile(r"\bP3_CANDIDATE (.+)$")
KV = re.compile(r"([a-z0-9_]+)=([^ ]+)")


def fields(line, pattern):
    match = pattern.search(line)
    return dict(KV.findall(match.group(1))) if match else None


def analyse(paths):
    samples = {}
    for source in paths:
        years = defaultdict(lambda: dict(elections=0, head_flips=0, mismatches=0,
                                         affected=0, eligible=0, air=0, air_score_changes=0,
                                         candidate_rank_flips=0, rank_up=0))
        examples = []
        for line in source.read_text(encoding="utf8", errors="replace").splitlines():
            row = fields(line, SUMMARY)
            if row:
                y = years[row["year"]]
                y["elections"] += 1
                y["head_flips"] += int(row["head_flip"])
                y["mismatches"] += int(row["head_match"] == "0")
                y["affected"] += int(row["affected"])
                y["eligible"] += int(row["eligible"])
                y["air"] += int(row["air"])
                if row["head_flip"] == "1" and len(examples) < 16:
                    examples.append(row)
                continue
            row = fields(line, CANDIDATE)
            if row:
                y = years[row["year"]]
                if row["mode"] == "air" and row["score0"] != row["score1"]:
                    y["air_score_changes"] += 1
                if int(row["rank0"]) >= 0 and int(row["rank1"]) >= 0 \
                        and row["rank0"] != row["rank1"]:
                    y["candidate_rank_flips"] += 1
                    if int(row["rank1"]) < int(row["rank0"]):
                        y["rank_up"] += 1
        samples[source.name] = {"years": dict(sorted(years.items())), "examples": examples}
    return {"sources": samples, "limitations": [
        "One election can repeat the same candidates; counts are not independent projects.",
        "Only selection-level affordability and C77 tiers are held fixed; future paths diverge after an actual purchase.",
        "A probe enabled in both arms has overhead and may perturb profit; do not use it for an adoption gate.",
    ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("engine_logs", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    paths = sorted(args.engine_logs.glob("*.log"))
    if not paths:
        p.error("aucun log")
    report = analyse(paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    for name, entry in report["sources"].items():
        print(name, {y: (r["elections"], r["head_flips"], r["mismatches"], r["affected"])
                     for y, r in entry["years"].items()})


if __name__ == "__main__":
    main()
