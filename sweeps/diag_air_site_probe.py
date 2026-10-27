#!/usr/bin/env python3
"""Offline AIR_SITE_PROBE reader (plain text / gzip), no engine dependencies.

One method per solo game. Only complete passes with equal START fingerprints
and exact start target dates across games enter the primary tables. `observed` retains invalid passes for diagnosis, never evidence.
A missing site scores zero relative to a positive oracle; absent oracle scores
and zero oracle denominators remain unknown. V4 checks every required leveling corner (bulk LevelTiles can partially succeed),
retaining V3 production admission and
acceptance >= 8. Ratios above one remain visible because scans span game ticks.
Slope totals are explicitly estimates: test-mode commands do not compose.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import re
import statistics

METHODS = ("spiral", "hybrid", "initial", "bands", "border", "funnel", "strict", "strict_full", "oracle", "ranked")
TAG = re.compile(r"\b(AIR_SITE_PROBE|AIR_PROBE_PASS|AIR_PROBE_START|AIR_PROBE_DONE)\s+(.*)")


def fields(text):
    # Native Squirrel concatenation in the first smoke; canonical writer now
    # emits literal null. Never parse the native token as a score string.
    text = re.sub(r"\(null\s*:\s*0x[0-9a-fA-F]+\)", "null", text)
    result = {}
    for key, raw in re.findall(r"(\w+)=([^\s]+)", text):
        if key in result:
            raise ValueError(f"duplicate field {key}")
        result[key] = None if raw == "null" else int(raw) if re.fullmatch(r"-?\d+", raw) else raw
    return result


def parse_text(text, source="memory", seed=None):
    """One fresh solo game, one method; partial passes are explicitly truncated."""
    rows, passes, issues = [], defaultdict(dict), []
    starts = []
    seen = set()
    for line, raw in enumerate(text.splitlines(), 1):
        match = TAG.search(raw)
        if not match:
            continue
        tag, payload = match.groups()
        try:
            f = fields(payload)
        except ValueError as exc:
            issues.append({"source": source, "line": line, "reason": str(exc)})
            continue
        if f.get("v") != 4 or f.get("method") not in METHODS:
            issues.append({"source": source, "line": line, "reason": "unsupported_version_or_method"})
            continue
        if tag == "AIR_PROBE_START":
            starts.append(f)
        elif tag == "AIR_PROBE_PASS":
            target, edge = f.get("target"), f.get("edge")
            if not isinstance(target, int) or edge not in ("begin", "end"):
                issues.append({"source": source, "line": line, "reason": "malformed_pass"})
            elif edge in passes[target]:
                issues.append({"source": source, "line": line, "reason": "duplicate_pass"})
            else:
                passes[target][edge] = {**f, "line": line}
        elif tag == "AIR_SITE_PROBE":
            required = {"v", "target", "town", "type", "method", "tile", "score", "oracle", "oracle_tile",
                        "center", "buildable", "error", "quote", "ops", "tiles", "tested", "begin", "end",
                        "levelable", "level_error", "level_quote", "admitted", "total_quote", "quote_exact",
                        "clear_quote", "catchment", "fallback", "level_complete"}
            if not required <= f.keys():
                issues.append({"source": source, "line": line, "reason": "malformed_row"})
                continue
            nullable = {"tile", "score", "oracle", "oracle_tile", "error", "quote", "level_error", "level_quote", "total_quote", "clear_quote"}
            numeric = required - nullable - {"method"}
            if any(not isinstance(f[k], int) for k in numeric) or any(f[k] < 0 for k in ("ops", "tiles", "tested")):
                issues.append({"source": source, "line": line, "reason": "invalid_numeric_field"})
                continue
            if any(f[k] is not None and not isinstance(f[k], int) for k in nullable):
                issues.append({"source": source, "line": line, "reason": "invalid_nullable_field"})
                continue
            if (f["center"] not in (0, 1) or f["buildable"] not in (0, 1)
                    or (f["tile"] is None) != (f["score"] is None)
                    or f["end"] < f["begin"]
                    or any(f[k] not in (0, 1) for k in ("levelable", "level_complete", "admitted", "quote_exact", "catchment"))
                    or (f["admitted"] == 1 and f["tile"] is None)
                    or (f["levelable"] == 1 and f["level_quote"] is None)
                    or (f["quote_exact"] == 1 and (f["buildable"] != 1 or f["total_quote"] != f["quote"]))
                    or (f["buildable"] == 1 and (f["tile"] is None or f["error"] != 0 or f["quote"] is None))):
                issues.append({"source": source, "line": line, "reason": "inconsistent_row"})
            identity = tuple(f[k] for k in ("target", "town", "type"))
            if identity in seen:
                issues.append({"source": source, "line": line, "reason": "duplicate_row", "key": identity})
            seen.add(identity)
            rows.append({**f, "source": source, "seed": seed, "line": line})
    if len(starts) != 1:
        issues.append({"source": source, "reason": "expected_one_start", "actual": len(starts)})
    method = starts[0].get("method") if starts else None
    if seed is None:
        issues.append({"source": source, "reason": "missing_seed"})
    pass_reports = []
    for target in sorted(set(passes) | {r["target"] for r in rows}):
        p = passes[target]
        begin, end = p.get("begin", {}), p.get("end", {})
        selected = [r for r in rows if r["target"] == target]
        reasons = []
        truncated = not begin or not end or end.get("truncated") != 0
        if truncated:
            reasons.append("truncated")
        if begin.get("date") != target or begin.get("fingerprint_end_date") != target:
            reasons.append("start_date_drift")
        if not begin.get("fingerprint"):
            reasons.append("missing_start_fingerprint")
        if not selected or begin.get("cases") != len(selected) or end.get("rows") != len(selected):
            reasons.append("row_count")
        if (any(r["method"] != method for r in selected)
                or begin.get("method") != method or end.get("method") != method):
            reasons.append("mixed_methods")
        if end.get("vehicles") != 0 or end.get("stations") != 0 or not starts or end.get("loan") != starts[0].get("loan"):
            reasons.append("mutation_or_missing_counters")
        if any(r["begin"] < target or r["end"] > end.get("date", -1)
               or not begin.get("line", 0) < r["line"] < end.get("line", 0) for r in selected):
            reasons.append("row_outside_pass")
        if issues:
            reasons.append("source_issues")
        for row in selected:
            row["valid"] = False  # Only analyse() may validate between separate games.
        pass_reports.append({"source": source, "seed": seed, "target": target, "method": method,
                             "valid": False, "local_valid": not reasons, "truncated": int(bool(truncated)),
                             "reasons": sorted(set(reasons)), "rows": len(selected), "begin": begin, "end": end})
    return {"rows": rows, "passes": pass_reports, "issues": issues}


def read_log(path, seed=None):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    if seed is None:
        match = re.search(r"seed(\d+)", path.name)
        seed = int(match[1]) if match else None
    with opener(path, "rt", encoding="utf-8", errors="strict") as handle:
        return parse_text(handle.read(), str(path.resolve()), seed)


def quantile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    return ordered[lo] + (ordered[min(lo + 1, len(ordered) - 1)] - ordered[lo]) * (pos - lo)


def ratio(row, feasible=False):
    if row["oracle"] is None or row["oracle"] <= 0:
        return None
    if row["tile"] is None or (feasible and (row["admitted"] != 1 or row["catchment"] != 1)):
        return 0.0
    return row["score"] / row["oracle"] if row["score"] is not None else None


def summary(rows):
    ratios = [r for row in rows if (r := ratio(row)) is not None]
    feasible = [r for row in rows if (r := ratio(row, True)) is not None]
    ops = [r["ops"] for r in rows]
    costs = [r["total_quote"] for r in rows if r["total_quote"] is not None]
    levels = [r["level_quote"] for r in rows if r["level_quote"] is not None]
    return {"n": len(rows), "ratio_n": len(ratios),
            "ratio_median": statistics.median(ratios) if ratios else None,
            "ratio_p10": quantile(ratios, .1),
            "ratio_mean": statistics.mean(ratios) if ratios else None,
            "ratio_equal_one": sum(v == 1 for v in ratios) / len(ratios) if ratios else None,
            "feasible_ratio_median": statistics.median(feasible) if feasible else None,
            "feasible_ratio_p10": quantile(feasible, .1),
            "feasible_ratio_mean": statistics.mean(feasible) if feasible else None,
            "constructible_share": sum(r["buildable"] == 1 for r in rows) / len(rows) if rows else None,
            "admitted_share": sum(r["admitted"] == 1 and r["catchment"] == 1 for r in rows) / len(rows) if rows else None,
            "levelable_share": sum(r["levelable"] == 1 for r in rows) / len(rows) if rows else None,
            "complete_level_share": sum(r["level_complete"] == 1 for r in rows) / len(rows) if rows else None,
            "partial_level_n": sum(r["levelable"] == 1 and r["level_complete"] == 0 and r["buildable"] == 0 for r in rows),
            "total_quote_median": statistics.median(costs) if costs else None,
            "total_quote_n": len(costs),
            "estimated_total_n": sum(r["total_quote"] is not None and r["quote_exact"] == 0 for r in rows),
            "level_quote_median": statistics.median(levels) if levels else None,
            "fallbacks": sum(r["fallback"] for r in rows),
            "miss_with_oracle": sum(r["tile"] is None and r["oracle_tile"] is not None for r in rows),
            "unusable_with_oracle": sum((r["tile"] is None or r["admitted"] != 1 or r["catchment"] != 1)
                                         and r["oracle_tile"] is not None for r in rows),
            "miss_with_positive_oracle": sum(r["tile"] is None and r["oracle"] is not None and r["oracle"] > 0 for r in rows),
            "unique_towns_missed_with_oracle": len({(r["seed"], r["town"]) for r in rows
                                                    if r["tile"] is None and r["oracle_tile"] is not None}),
            "error_263": sum(r["error"] == 263 for r in rows),
            "center_uncovered": sum(r["tile"] is not None and r["center"] == 0 for r in rows),
            "ops_median": statistics.median(ops) if ops else None, "ops_total": sum(ops) if ops else None}


def tables(rows):
    groups, towns = defaultdict(list), defaultdict(list)
    ref = {(r["seed"], r["target"], r["town"], r["type"]): r for r in rows if r["method"] == "spiral"}
    paired = []
    for row in rows:
        groups[row["method"]].append(row)
        towns[(row["seed"], row["town"], row["method"])].append(row)
        other = ref.get((row["seed"], row["target"], row["town"], row["type"]))
        if other is None:
            continue
        a, b = ratio(row), ratio(other)
        paired.append({k: row[k] for k in ("source", "seed", "target", "town", "type", "method", "line", "valid")}
                      | {"score_delta": row["score"] - other["score"] if row["score"] is not None and other["score"] is not None else None,
                         "ratio_delta": a - b if a is not None and b is not None else None,
                         "total_quote_delta": row["total_quote"] - other["total_quote"]
                             if row["total_quote"] is not None and other["total_quote"] is not None else None,
                         "ops_delta": row["ops"] - other["ops"], "reference_line": other["line"], "reference_source": other["source"]})
    return {"by_method": {name: summary(groups[name]) for name in METHODS},
            "by_town": [{"seed": key[0], "town": key[1], "method": key[2], **summary(items)} for key, items in towns.items()],
            "paired": paired}


def analyse(parsed):
    rows = [dict(r) for p in parsed for r in p["rows"]]
    passes = [{**p, "reasons": list(p["reasons"])} for stream in parsed for p in stream["passes"]]
    groups = defaultdict(list)
    for p in passes:
        groups[(p["seed"], p["target"])].append(p)
    comparisons = []
    for (seed, target), group in groups.items():
        reasons = set()
        if sorted(p["method"] or "" for p in group) != sorted(METHODS):
            reasons.add("method_coverage_or_duplicate_game")
        if any(not p["local_valid"] for p in group):
            reasons.add("invalid_or_truncated_pass")
        fingerprints = {p["begin"].get("fingerprint") for p in group}
        if len(fingerprints) != 1 or None in fingerprints:
            reasons.add("start_fingerprint_mismatch")
        selected = [r for r in rows if r["seed"] == seed and r["target"] == target]
        keys = []
        for p in group:
            keys.append({(r["town"], r["type"]) for r in selected if r["source"] == p["source"]})
        if not keys or any(k != keys[0] for k in keys):
            reasons.add("town_type_coverage_mismatch")
        oracle_rows = [r for r in selected if r["method"] == "oracle"]
        oracle = {(r["town"], r["type"]): r for r in oracle_rows}
        if len(oracle) != len(oracle_rows):
            reasons.add("duplicate_oracle")
        for row in selected:
            found = oracle.get((row["town"], row["type"]))
            row["oracle"] = found["score"] if found else None
            row["oracle_tile"] = found["tile"] if found else None
            row["oracle_source"] = found["source"] if found else None
            row["oracle_line"] = found["line"] if found else None
            row["oracle_begin"] = found["begin"] if found else None
            row["oracle_end"] = found["end"] if found else None
            row["oracle_total_quote"] = found["total_quote"] if found else None
            row["oracle_quote_exact"] = found["quote_exact"] if found else None
            row["valid"] = not reasons
        for p in group:
            p["reasons"] = sorted(set(p["reasons"]) | reasons)
            p["valid"] = not reasons
        comparisons.append({"seed": seed, "target": target, "valid": not reasons,
                            "reasons": sorted(reasons), "method_count": len(group),
                            "cases": len(keys[0]) if keys else 0})
    valid_rows = [r for r in rows if r["valid"]]
    return {"schema": 4, "protocol": "separate_solo_games_equal_start_fingerprint_leveling_admission", "passes": passes,
            "comparisons": comparisons, "issues": [r for p in parsed for r in p["issues"]],
            "valid": tables(valid_rows), "by_date": {str(date): tables([r for r in valid_rows if r["target"] == date])
                for date in sorted({r["target"] for r in rows})},
            "observed_invalid_not_evidence": tables([r for r in rows if not r["valid"]]), "rows": rows}


def probe_health(health, analysis, seeds, years):
    """Expected inactivity is not an engine failure. Preserve raw health verdicts."""
    engine_ok = bool(health) and len(health) == len(seeds) * len(METHODS)
    for item in health.values():
        company = item.get("companies", {}).get("OpexAI", {})
        engine_ok = engine_ok and not item.get("engine_error") and not item.get("unattributed_errors")
        engine_ok = engine_ok and not company.get("script_errors") and company.get("horizon_complete", False)
        engine_ok = engine_ok and company.get("company_present", False) and not company.get("bankrupt", True)
        checkpoints = item.get("checkpoint_report", {})
        engine_ok = engine_ok and not checkpoints.get("duplicates") and not checkpoints.get("missing_companies")
        engine_ok = engine_ok and not any(checkpoints.get("missing_checkpoints", {}).values())
    # OpenTTD uses year zero; these targets are emitted by AIDate.GetDate.
    targets = {719529} if years == 1 else {719529, 720258, 721354}
    comparisons = analysis["comparisons"]
    expected = {(seed, date) for seed in seeds for date in targets}
    actual = {(p["seed"], p["target"]) for p in comparisons}
    coverage = actual == expected and len(comparisons) == len(expected)
    valid = coverage and not analysis["issues"] and all(p["valid"] for p in comparisons)
    return {"engine_script_horizon_ok": bool(engine_ok), "expected_inactive_company": True,
            "required_dates_per_seed": len(targets), "comparison_coverage_complete": coverage,
            "measurement_valid": valid, "smoke_ok": bool(engine_ok and valid)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = analyse([read_log(p) for p in args.logs])
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passes": [{k: p[k] for k in ("seed", "target", "valid", "reasons", "rows")} for p in result["passes"]],
                      "valid": result["valid"]["by_method"]}, indent=2))


if __name__ == "__main__":
    main()
