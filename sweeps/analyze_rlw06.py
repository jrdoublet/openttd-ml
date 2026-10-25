"""Analyse RLW-06 dans les journaux moteur reference_seed*_r*.log.

Le dernier RLW06_SUMMARY est un instantane cumulatif par partie ; les STEP
journalises sont echantillonnes pendant search (1/32), donc leur somme ne
remplace jamais le total_ops/ticks du SUMMARY.

Usage:
  python -X utf8 sweeps/analyze_rlw06.py results/MY_RUN_engine --require-complete
  python -X utf8 sweeps/analyze_rlw06.py results/OFF_engine --expect-off
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


FILE = re.compile(r"^reference_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")
EVENT = re.compile(
    r"\bOPEX\s+(?P<date>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<kind>RLW04B_(?:CARGO|ENUM)|RLW06_[A-Z_]+)\s*(?P<fields>.*)$"
)
FIELD = re.compile(r"(?P<name>[A-Za-z_][A-Za-z_0-9]*)=(?P<value>\S+)")
SUMMARY_FIELDS = (
    "best", "starts", "failed", "searches", "ready", "stored", "reused",
    "expired", "deferred", "slices", "init_ops", "astar_ops",
    "finalize_ops", "total_ops", "ticks", "cross", "max_init",
    "max_slice",
)


def _number(value, default=None):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_events(log):
    """Preserve log order, even when multiple events share a game date."""
    with Path(log).open(encoding="utf-8", errors="replace") as stream:
        for lineno, line in enumerate(stream, 1):
            match = EVENT.search(line)
            if match is None:
                continue
            row = dict(FIELD.findall(match["fields"]))
            row.update(kind=match["kind"], date=match["date"], line=lineno)
            yield row


def analyse(log):
    """Per-log event chain, final SUMMARY and explicitly observed STEP costs."""
    path = Path(log)
    match = FILE.fullmatch(path.name)
    if match is None:
        raise ValueError("Unexpected engine log filename: " + path.name)
    events = Counter()
    chains = {}
    last_summary = None
    summaries = 0
    enum_done = False
    last_enum = None
    measured = {"steps": 0, "logged_ops": 0, "logged_ticks": 0,
                "crossed_steps": 0, "max_step_ops": 0, "by_stage": {}}
    for row in parse_events(path):
        kind = row["kind"]
        events[kind] += 1
        if kind == "RLW04B_ENUM":
            last_enum = {k: _number(v, v) for k, v in row.items()}
            if row.get("phase") == "done":
                enum_done = True
            continue
        if kind.startswith("RLW04B_"):
            continue
        if kind == "RLW06_SUMMARY":
            summaries += 1
            last_summary = {field: _number(row.get(field)) for field in SUMMARY_FIELDS}
            last_summary["date"] = row["date"]
            last_summary["line"] = row["line"]
            continue
        # SUMMARY uses key=-; stock re-use and expiry use pair= rather than key=.
        key = row.get("pair") or row.get("key")
        if not key or key == "-":
            continue
        chain = chains.setdefault(key, {
            "key": key, "pair": None, "astar": None, "ready": None,
            "reuse": None, "end": None, "expire": None, "step_count": 0,
        })
        stage = kind.removeprefix("RLW06_").lower()
        if stage in ("pair", "astar", "ready", "reuse", "end", "expire"):
            # Keep the latest event, retaining all fields and log/date provenance.
            chain[stage] = dict(row)
        if kind == "RLW06_STEP":
            chain["step_count"] += 1
            measured["steps"] += 1
            ops = _number(row.get("opcodes"), 0)
            ticks = _number(row.get("ticks"), 0)
            measured["logged_ops"] += ops
            measured["logged_ticks"] += ticks
            measured["crossed_steps"] += int(ticks > 0)
            measured["max_step_ops"] = max(measured["max_step_ops"], ops)
            phase = row.get("stage", "unknown")
            bucket = measured["by_stage"].setdefault(
                phase, {"steps": 0, "logged_ops": 0, "logged_ticks": 0}
            )
            bucket["steps"] += 1
            bucket["logged_ops"] += ops
            bucket["logged_ticks"] += ticks

    linked = {
        "pair": sum(c["pair"] is not None for c in chains.values()),
        "pair_to_astar": sum(c["pair"] is not None and c["astar"] is not None
                             and c["pair"]["line"] < c["astar"]["line"]
                             for c in chains.values()),
        "pair_to_astar_to_ready": sum(
            all(c[k] is not None for k in ("pair", "astar", "ready"))
            and c["pair"]["line"] < c["astar"]["line"] < c["ready"]["line"]
            for c in chains.values()
        ),
        "pair_to_astar_to_ready_to_reuse": sum(
            all(c[k] is not None for k in ("pair", "astar", "ready", "reuse"))
            and c["pair"]["line"] < c["astar"]["line"] < c["ready"]["line"]
                < c["reuse"]["line"]
            for c in chains.values()
        ),
    }
    return {
        "log": path.name, "seed": int(match["seed"]),
        "repeat": int(match["repeat"]), "enum_done": enum_done,
        "last_enum": last_enum, "summary_count": summaries,
        "summary_present": summaries > 0, "last_summary": last_summary,
        "events": dict(sorted(events.items())), "chain_counts": linked,
        "chains": [chains[key] for key in sorted(chains)],
        "observed_steps": measured,
    }


def aggregate(rows):
    """Sum only the *last* per-run cumulative summary for each seed."""
    by_seed = defaultdict(list)
    for row in rows:
        by_seed[row["seed"]].append(row)

    def rollup(items):
        counters = Counter()
        measured = Counter()
        for item in items:
            counters.update(item["chain_counts"])
            measured["logged_ops"] += item["observed_steps"]["logged_ops"]
            measured["logged_ticks"] += item["observed_steps"]["logged_ticks"]
            measured["steps"] += item["observed_steps"]["steps"]
        totals = {
            key: sum(r["last_summary"][key] for r in items
                     if r["last_summary"] is not None
                     and r["last_summary"][key] is not None)
            for key in SUMMARY_FIELDS
        }
        return {
            "runs": len(items),
            "enum_done_runs": sum(r["enum_done"] for r in items),
            "summary_runs": sum(r["summary_present"] for r in items),
            "chains": dict(counters),
            "last_summary_totals": totals,
            "observed_step_totals": dict(measured),
        }

    return {
        "runs": rows,
        "by_seed": {str(seed): rollup(items)
                    for seed, items in sorted(by_seed.items())},
        "totals": rollup(rows),
    }


def check(rows, require_complete=False, expect_off=False):
    """Raise a clear exception on protocol violations."""
    errors = []
    for row in rows:
        if require_complete:
            if not row["enum_done"]:
                errors.append(row["log"] + ": RLW04B_ENUM phase=done absent")
            if not row["summary_present"]:
                errors.append(row["log"] + ": RLW06_SUMMARY absent")
        if expect_off:
            emitted = {key: count for key, count in row["events"].items()
                       if key.startswith(("RLW06_", "RLW04B_")) and count}
            if emitted:
                errors.append(row["log"] + ": probe OFF emitted " + str(emitted))
    if errors:
        raise ValueError("; ".join(errors))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_directory", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--expect-off", action="store_true")
    args = parser.parse_args(argv)
    logs = sorted(args.log_directory.glob("reference_seed*_r*.log"))
    if not logs:
        parser.error("No reference_seed*_r*.log files found")
    try:
        rows = [analyse(log) for log in logs]
        check(rows, require_complete=args.require_complete, expect_off=args.expect_off)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(aggregate(rows), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
