#!/usr/bin/env python3
"""V241: descriptive, read-only VIVIER top-K exposure in existing engine logs.

Usage:
  python -B -X utf8 sweeps/diag_v241_topk_recent_logs.py PATH [PATH ...]

PATH is a *_seedN_rR.log[.gz] or an engine-log directory. Output is JSON on
stdout; no file is created. The default PROJECT_TOP_K=64 is an observational
threshold, NOT an intervention. No causal profit or alternative K is estimated.
"""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from statistics import mean, median


TOP_K = 64
NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$")
VIVIER = re.compile(
    r"\[0\]\s+\[I\]\s+OPEX\s+(?P<year>\d{4})-\d{1,2}-\d{1,2}"
    r"\s+VIVIER\s+(?P<fields>[^\r\n]*)"
)
KV = re.compile(r"\b([A-Za-z_][A-Za-z_0-9]*)=(\S+)")
NUMBERS = ("selected", "not_selected", "considered", "sel_ops")


def _read_binary(path):
    return gzip.open(path, "rb") if str(path).endswith(".gz") else open(path, "rb")


def content_sha256(path):
    """Hash decompressed bytes; exact conflicting .log/.gz copies fail closed."""
    digest = hashlib.sha256()
    with _read_binary(path) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(inputs):
    """Return independent logical logs and provenance of equivalent copies."""
    files = {}
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            candidates = (file for file in path.iterdir()
                          if file.is_file() and NAME.fullmatch(file.name))
        elif path.is_file() and NAME.fullmatch(path.name):
            candidates = (path,)
        else:
            raise ValueError(f"not an existing V241 engine log/directory: {path}")
        for file in candidates:
            resolved = file.resolve()
            files[str(resolved)] = resolved
    if not files:
        raise ValueError("no *_seedN_rR.log[.gz] found")
    by_game = defaultdict(list)
    for file in files.values():
        basename = file.name[:-3] if file.suffix == ".gz" else file.name
        by_game[(str(file.parent), basename)].append(file)
    chosen = []
    canonical_games = {}
    for (directory, basename), copies in sorted(by_game.items()):
        copies.sort(key=lambda p: (p.suffix == ".gz", str(p)))
        signatures = [(path, content_sha256(path)) for path in copies]
        if len({value for _, value in signatures}) != 1:
            raise ValueError(
                f"contradictory .log/.gz copies: {', '.join(str(p) for p, _ in signatures)}"
            )
        match = NAME.fullmatch(basename)
        canonical = (directory, match["arm"], int(match["seed"]), int(match["repeat"]))
        if canonical in canonical_games and canonical_games[canonical] != basename:
            raise ValueError(
                f"ambiguous V241 game identity: {canonical_games[canonical]} / {basename}"
            )
        canonical_games[canonical] = basename
        chosen.append({
            "path": copies[0], "directory": directory, "arm": match["arm"],
            "seed": int(match["seed"]), "repeat": int(match["repeat"]),
            "source_files": [str(file) for file in copies],
            "sha256_decompressed": signatures[0][1],
        })
    return chosen


def parse_events(file):
    """One VIVIER line == one observed selection call, even if repeated."""
    with (gzip.open(file, "rt", encoding="utf-8", errors="replace")
          if str(file).endswith(".gz")
          else open(file, "rt", encoding="utf-8", errors="replace")) as stream:
        for line in stream:
            found = VIVIER.search(line)
            if not found:
                continue  # VIVIER_MIX and VIVIER_DIV are NOT selection calls.
            pairs = KV.findall(found["fields"])
            if len(pairs) != len({key for key, _ in pairs}):
                raise ValueError(f"duplicate VIVIER field in {file}: {found['fields']}")
            fields = dict(pairs)
            parsed = {}
            invalid = []
            for key in NUMBERS:
                raw = fields.get(key)
                try:
                    number = int(raw) if raw is not None else None
                    if number is not None and number < 0:
                        raise ValueError("negative counter")
                except ValueError:
                    number = None
                    invalid.append(key)
                parsed[key] = number
            yield {
                "year": int(found["year"]),
                "path": fields.get("path"),  # None != observed numeric zero.
                **parsed,
                "invalid_numeric_fields": invalid,
            }


def cost_stats(samples):
    """Observed-only sel_ops; 0 is a measured cost, None is not."""
    return {
        "observed_calls": len(samples),
        "sum": sum(samples) if samples else None,
        "mean": round(mean(samples), 3) if samples else None,
        "median": median(samples) if samples else None,
        "min": min(samples) if samples else None,
        "max": max(samples) if samples else None,
    }


def summarize(events):
    counts = Counter()
    missing = Counter()
    invalid = Counter()
    numeric = defaultdict(list)
    cost = defaultdict(list)
    for event in events:
        counts["calls"] += 1
        for key in NUMBERS:
            value = event[key]
            if value is None:
                missing[key] += 1
            else:
                numeric[key].append(value)
        for key in event["invalid_numeric_fields"]:
            invalid[key] += 1
        if event["path"] is None:
            missing["path"] += 1
        selected = event["selected"]
        if selected is None:
            category = "unknown_cap"
        elif selected >= TOP_K:
            category = "cap_reached"
        else:
            category = "not_cap"
        counts[category] += 1
        if category == "cap_reached":
            considered = event["considered"]
            not_selected = event["not_selected"]
            if (selected == TOP_K and considered == selected
                    and not_selected == 0):
                counts["cap_exact_fit"] += 1
            elif (selected == TOP_K and considered is not None
                    and not_selected is not None and considered > selected
                    and not_selected == considered - selected):
                counts["cap_with_unselected"] += 1
            else:
                counts["cap_unresolved"] += 1
        if selected is not None:
            counts["selected_positive" if selected > 0 else "selected_zero"] += 1
        if event["sel_ops"] is not None:
            cost[category].append(event["sel_ops"])
    known = counts["cap_reached"] + counts["not_cap"]
    return {
        "calls": counts["calls"],
        "cap_reached_selected_ge_64": counts["cap_reached"],
        "cap_reached_exact_fit_no_unselected": counts["cap_exact_fit"],
        "cap_reached_with_unselected": counts["cap_with_unselected"],
        "cap_reached_insufficient_or_inconsistent": counts["cap_unresolved"],
        "not_cap_selected_lt_64": counts["not_cap"],
        "unknown_cap_selected_missing_or_invalid": counts["unknown_cap"],
        "cap_fraction_known_selected": (
            round(counts["cap_reached"] / known, 6) if known else None
        ),
        "cap_fraction_all_calls_lower_bound": (
            round(counts["cap_reached"] / counts["calls"], 6) if counts["calls"] else None
        ),
        "selected_positive_calls": counts["selected_positive"],
        "selected_zero_calls": counts["selected_zero"],
        "field_coverage": {
            key: {"observed": len(numeric[key]), "missing_or_invalid": missing[key],
                  "invalid": invalid[key], "zero": sum(n == 0 for n in numeric[key]),
                  "sum": sum(numeric[key]) if numeric[key] else None}
            for key in NUMBERS
        },
        "path_missing": missing["path"],
        "sel_ops_by_cap": {
            group: {**cost_stats(cost[group]),
                    "calls_missing_or_invalid_sel_ops": counts[group] - len(cost[group])}
            for group in ("cap_reached", "not_cap", "unknown_cap")
        },
    }


def analyze(inputs):
    files = collect(inputs)
    groups = defaultdict(list)
    per_file = []
    for log in files:
        n = 0
        for event in parse_events(log["path"]):
            key = (log["directory"], log["arm"], log["seed"], log["repeat"],
                   event["year"], event["path"])
            groups[key].append(event)
            n += 1
        per_file.append({
            "arm": log["arm"], "seed": log["seed"], "repeat": log["repeat"],
            "directory": log["directory"], "source_files": log["source_files"],
            "sha256_decompressed": log["sha256_decompressed"],
            "vivier_calls": n if n else None,
            "logged_vivier_events": n,
            "vivier_coverage": "observed" if n else "unknown_no_vivier_marker",
        })
    grouped = []
    for (directory, arm, seed, repeat, year, path), rows in sorted(
        groups.items(), key=lambda item: (item[0][0], item[0][1], item[0][2],
                                         item[0][3], item[0][4], item[0][5] or "")
    ):
        grouped.append({
            "directory": directory, "arm": arm, "seed": seed,
            "repeat": repeat, "year": year, "path": path,
            **summarize(rows),
        })
    observed_logs = sum(row["vivier_coverage"] == "observed" for row in per_file)
    logged_calls = sum(group["calls"] for group in grouped)
    return {
        "scope": "VIVIER selection calls only; no construction or causal profitability inferred",
        "cap_definition": "selected >= 64; selected > 0 alone is NOT cap",
        "logical_log_count": len(files),
        "physical_file_count": sum(len(log["source_files"]) for log in files),
        "duplicate_log_gzip_copies_ignored": (
            sum(len(log["source_files"]) - 1 for log in files)
        ),
        "total_vivier_calls": logged_calls if observed_logs == len(files) else None,
        "logged_vivier_events": logged_calls,
        "vivier_coverage": {
            "observed_log_count": observed_logs,
            "unknown_log_count": len(files) - observed_logs,
            "status": ("observed" if observed_logs == len(files) else
                       "unknown" if observed_logs == 0 else "partial"),
        },
        "files": per_file,
        "groups": grouped,
        "limitations": [
            "No inference of constructed lines, counterfactual K, or causal ROI.",
            "Every VIVIER line is a call, even if the same date and fields repeat.",
            "Missing/invalid selected cannot be classified as cap or non-cap.",
            "No VIVIER marker in a log means uninstrumented or unobserved selection, not proven zero calls.",
            "Costs are reported by cap category only with observed sel_ops.",
            "Identical compressed/plain copies are one game; differing bytes fail closed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.inputs)
    except (OSError, ValueError, EOFError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
