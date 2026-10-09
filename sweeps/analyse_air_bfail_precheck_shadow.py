#!/usr/bin/env python3
"""Relie un prétest B purement passif à l'issue physique du même chantier AIR.

Le champ pre_b_ok ne doit JAMAIS être traité comme une prédiction de succès
du chantier : l'autorité et le nivellement ont des issues différées. Le coût
historique de A exposé n'est ni une restitution cash ni un gain contrefactuel.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from parse_air_finance_margin import RE_KV, clean_log_line, parse_kv_payload, parse_log_filename


PATTERN = re.compile(r"\bAIR_FINANCE_TRY\s+(.*)$")
REQUIRED = ("date", "path", "outcome", "reason", "new_airports",
            "pre_b_ok", "pre_b_err", "pre_b_verdict", "pre_b_anchor",
            "real_b_err", "actual", "c_level_a", "c_airport_a")
NUMBERS = ("new_airports", "pre_b_ok", "pre_b_err", "pre_b_anchor",
           "real_b_err", "actual", "c_level_a", "c_airport_a")
VERDICTS = {"reject", "accept", "defer_level", "defer_authority"}
AFTER_B_OK = {"OK", "STNFAIL", "HANGAR", "PLANE", "ORDFAIL", "START"}


def analyze_lines(lines, filename):
    meta = parse_log_filename(filename)
    if not meta["arm"] or "seed" not in Path(filename).stem:
        raise ValueError(f"identity missing: {filename}")
    rows = []
    warnings = []
    all_two_new_tries = 0
    for line_no, text in enumerate(lines, 1):
        hit = PATTERN.search(clean_log_line(text))
        if hit is None:
            continue
        payload = hit.group(1)
        keys = [m.group(1) for m in RE_KV.finditer(payload)]
        if len(set(keys)) != len(keys):
            warnings.append({"line": line_no, "code": "duplicate_fields"})
            continue
        raw = parse_kv_payload(payload)
        if raw.get("outcome") == "refused_margin" or raw.get("outcome") == "refused_capital":
            continue
        if raw.get("new_airports") != "2":
            continue
        all_two_new_tries += 1
        missing = [name for name in REQUIRED if name not in raw]
        if missing:
            warnings.append({"line": line_no, "code": "missing_fields", "fields": missing})
            continue
        if any(not raw[name].isdecimal() for name in NUMBERS):
            warnings.append({"line": line_no, "code": "invalid_integer"})
            continue
        record = {name: int(raw[name]) for name in NUMBERS}
        if (record["pre_b_ok"] not in (0, 1) or raw["pre_b_verdict"] not in VERDICTS
                or (record["pre_b_ok"] == 0) != (raw["pre_b_verdict"] == "reject")
                or record["pre_b_anchor"] < 0):
            warnings.append({"line": line_no, "code": "invalid_preflight_verdict"})
            continue
        reason = raw["reason"]
        if reason == "BFAIL":
            category = "correct_early_reject" if record["pre_b_ok"] == 0 else "missed_bfail"
        elif reason in AFTER_B_OK:
            category = "false_reject" if record["pre_b_ok"] == 0 else "not_rejected_after_b"
        elif reason == "AFAIL":
            category = "a_failed_first"
        else:
            category = "unresolved_other"
        row = {"line": line_no, "seed": meta["seed"], "arm": meta["arm"],
               "repeat": meta["repeat"], "date": raw["date"], "path": raw["path"],
               "reason": reason, "outcome": raw["outcome"],
               "pre_b_verdict": raw["pre_b_verdict"], "category": category,
               "real_b_stage": raw.get("real_b_stage"),
               "a_historical_spend_gbp": (record["c_level_a"] + record["c_airport_a"]),
               **record}
        if row["real_b_stage"] is None:
            warnings.append({"line": line_no, "code": "missing_real_b_stage"})
        elif row["real_b_stage"] not in ("level", "airport", "built", "not_attempted"):
            warnings.append({"line": line_no, "code": "invalid_real_b_stage"})
        rows.append(row)
    counts = Counter(r["category"] for r in rows)
    return {"file": filename, "seed": meta["seed"], "arm": meta["arm"],
            "repeat": meta["repeat"], "all_two_new_tries": all_two_new_tries,
            "parsed_two_new_tries": len(rows), "status_counts": dict(counts),
            "precheck_error_codes": dict(Counter(str(r["pre_b_err"]) for r in rows)),
            "real_b_stages": dict(Counter(r["real_b_stage"] or "unknown" for r in rows)),
            "first_reject_eligible_a_spend_gbp": sum(r["a_historical_spend_gbp"]
                for r in rows if r["category"] == "correct_early_reject"),
            "missed_bfail_a_spend_gbp": sum(r["a_historical_spend_gbp"]
                for r in rows if r["category"] == "missed_bfail"),
            "rows": rows, "warnings": warnings}


def analyze(paths):
    runs = []
    seen = set()
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as stream:
            run = analyze_lines(stream, path.name)
        identity = (run["arm"], run["seed"], run["repeat"])
        if identity in seen:
            raise ValueError(f"duplicate run {identity}")
        seen.add(identity)
        runs.append(run)
    counter = Counter()
    for run in runs:
        counter.update(run["status_counts"])
    return {"runs": runs, "summary": {"runs": len(runs),
        "attempts": sum(r["all_two_new_tries"] for r in runs),
        "parsed_attempts": sum(r["parsed_two_new_tries"] for r in runs),
        "status_counts": dict(counter),
        "eligible_historical_a_spend_gbp": sum(r["first_reject_eligible_a_spend_gbp"] for r in runs),
        "missed_historical_a_spend_gbp": sum(r["missed_bfail_a_spend_gbp"] for r in runs),
        "warnings": sum(len(r["warnings"]) for r in runs)},
        "caveat": "observational signal with opcode/timing perturbation; no avoided cash or policy effect"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)
    result = analyze(args.logs)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
