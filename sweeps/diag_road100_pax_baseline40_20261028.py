#!/usr/bin/env python3
"""Recompute descriptive PAX calibration on the frozen ROAD-only 40x5 baseline.

This does NOT fit or recommend a runtime coefficient. LINE_REVENUE is a
line/vehicle-profit observation, not the company's profit_year; observations
on the same line at different ages are correlated. No imputation for lines
that never got built or did not survive to age >= 2.
"""

import argparse
import gzip
import json
from pathlib import Path
import re
from statistics import median

from diag_road100_pax_heldout_20261028 import FIELD, RECORD, parse_log


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOGS = ROOT / "results/road100_baseline_40x5_20261027_engine"
LOG_NAME = re.compile(r"road100_baseline_seed(\d+)_r0\.log(?:\.gz)?")


def discover(directory):
    directory = Path(directory)
    files = sorted(directory.glob("road100_baseline_seed*_r0.log"))
    files += sorted(directory.glob("road100_baseline_seed*_r0.log.gz"))
    if len(files) != 40:
        raise ValueError(f"expected exactly 40 baseline logs, got {len(files)}")
    seen = set()
    found = []
    for path in files:
        match = LOG_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"unexpected filename: {path}")
        seed = int(match[1])
        if seed in seen:
            raise ValueError(f"duplicate seed: {seed}")
        seen.add(seed)
        found.append((seed, path))
    return found


def summarise(rows):
    out = {
        "observations": len(rows),
        "distinct_lines": len({(r["seed"], r["line"]) for r in rows}),
        "seeds_with_mature_pax": len({r["seed"] for r in rows}),
    }
    for kind in ("rev", "prof"):
        pred, real = f"pred_{kind}", f"real_{kind}"
        positive = [r for r in rows if r[pred] > 0 and r[real] > 0]
        denominator = sum(r[pred] for r in rows)
        out[kind] = {
            "ratio_of_sums": round(sum(r[real] for r in rows) / denominator, 6)
            if denominator > 0 else None,
            "median_positive_line_age_ratio": round(
                median(r[real] / r[pred] for r in positive), 6
            ) if positive else None,
            "n_positive": len(positive),
            "n_nonpositive_excluded_from_median": len(rows) - len(positive),
        }
    return out


def read_all_ages(path, seed):
    """Supplementary all-ages median, explicitly NOT the mature calibration."""
    opening = gzip.open if str(path).endswith(".gz") else open
    rows = []
    seen = set()
    with opening(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line_no, raw in enumerate(stream, 1):
            if RECORD not in raw:
                continue
            fields = {}
            for token in raw.split(RECORD, 1)[1].split():
                parsed = FIELD.fullmatch(token)
                if parsed is None:
                    raise ValueError(f"invalid event {path}:{line_no}")
                key, value = parsed.groups()
                if key in fields:
                    raise ValueError(f"duplicate field {path}:{line_no}: {key}")
                fields[key] = value
            if fields.get("mode") != "road" or fields.get("kind") != "pax":
                continue
            age, line = int(fields["age"]), int(fields["line"])
            identity = (seed, line, age)
            if identity in seen:
                raise ValueError(f"duplicate line-age {identity}")
            seen.add(identity)
            entry = {"seed": seed, "line": line, "age": age}
            for field in ("pred_rev", "real_rev", "pred_prof", "real_prof"):
                entry[field] = float(fields[field])
            rows.append(entry)
    return rows


def analyse(directory=DEFAULT_LOGS):
    by_seed = {}
    all_rows = []
    all_ages = []
    immature = 0
    for seed, path in discover(directory):
        rows, counts = parse_log(path, seed)
        by_seed[seed] = len(rows)
        all_rows.extend(rows)
        all_ages.extend(read_all_ages(path, seed))
        immature += counts["immature_age_lt_2"]
    return {
        "source": str(Path(directory)),
        "design": "40 ROAD-only baseline logs; OpexAI LINE_REVENUE road/pax age>=2",
        "all": summarise(all_rows),
        "all_reported_ages_not_a_mature_calibration": summarise(all_ages),
        "age2": summarise([r for r in all_rows if r["age"] == 2]),
        "age3plus": summarise([r for r in all_rows if r["age"] >= 3]),
        "by_year": {str(year): summarise([r for r in all_rows if r["year"] == year])
                    for year in sorted({r["year"] for r in all_rows})},
        "immature_excluded": immature,
        "seeds_without_mature_pax": sorted(seed for seed, n in by_seed.items() if n == 0),
        "caveats": [
            "The 40 seeds are experimental units; line-age rows are not independent.",
            "real_prof is vehicle GetProfitLastYear, not company profit_year.",
            "Only built/surviving lines appear; no causal prediction of unbuilt PAX.",
            "The baseline and the V24 ON heldout sample are different policies and cohorts.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    output = json.dumps(analyse(args.logs), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
