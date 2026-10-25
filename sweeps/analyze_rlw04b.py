"""Read RLW-04b cargo qualification and native enumeration diagnostics.

Usage: python -X utf8 sweeps/analyze_rlw04b.py results/CAMPAIGN_engine
"""
import argparse
import json
import re
from pathlib import Path

EVENT = re.compile(r"\bOPEX (\d{4}-\d{1,2}-\d{1,2}) (RLW04B_CARGO|RLW04B_ENUM)\s+(.*)")
FIELD = re.compile(r"(\w+)=([^\s]+)")


def analyse(log: Path):
    cargos = []
    phases = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = EVENT.search(line)
        if not m:
            continue
        row = dict(FIELD.findall(m[3]))
        row["date"] = m[1]
        if m[2] == "RLW04B_CARGO":
            cargos.append(row)
        else:
            phases.append(row)
    final = next((r for r in reversed(phases) if r.get("phase") == "done"), None)
    last = final or (phases[-1] if phases else {})
    return {
        "log": log.name,
        "cargo_count": len(cargos),
        "cargos": cargos,
        "completed": final is not None,
        "days": int(last.get("days", -1)),
        "sources": int(last.get("sources", 0)),
        "slices": int(last.get("slices", 0)),
        "pairs": int(last.get("pairs", 0)),
        "total_ops": int(last.get("total_ops", 0)),
        "init_ops": int(last.get("init_ops", 0)),
        "max_ops": int(last.get("max_ops", 0)),
        "init_max_ops": int(last.get("init_max", 0)),
        "overruns": int(last.get("overruns", 0)),
        "tick_crossings": int(last.get("ticks", 0)),
        "too_many_sinks": int(last.get("too_many_sinks", 0)),
        "low": int(last.get("low", 0)),
        "mid": int(last.get("mid", 0)),
        "high": int(last.get("high", 0)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log_directory", type=Path)
    ap.add_argument("--expect-off", action="store_true")
    ap.add_argument("--require-complete", action="store_true")
    ap.add_argument("--max-days", type=int)
    args = ap.parse_args()
    logs = sorted(args.log_directory.glob("reference_seed*_r*.log"))
    if not logs:
        ap.error("No reference_seed*_r*.log files found")
    rows = [analyse(log) for log in logs]
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    for row in rows:
        if args.expect_off and (row["cargos"] or row["slices"] or row["pairs"]):
            ap.error("Probe OFF emitted RLW-04b events: " + row["log"])
        if args.require_complete and not row["completed"]:
            ap.error("Pass not completed: " + row["log"])
        if args.max_days is not None and row["days"] > args.max_days:
            ap.error("Slow pass: " + row["log"])
        if row["overruns"] or row["tick_crossings"]:
            ap.error("Opcode overrun in " + row["log"])


if __name__ == "__main__":
    main()
