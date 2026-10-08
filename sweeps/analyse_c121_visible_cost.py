"""Closed accounting periods from the passive copied-AI fleet cost fixture."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from analyse_c121_pax_flux import numeric_fields


def decode_cost(text):
    periods, pending = [], []
    for line in text.splitlines():
        if "[0] [I] C121_VISIBLE_COST_QUOTE " in line:
            row = numeric_fields(line.split("C121_VISIBLE_COST_QUOTE ", 1)[1])
            if any(not isinstance(row.get(k), int) or row[k] < 0 for k in ("ops", "ticks", "line", "vehicles")):
                raise ValueError("invalid quote cost")
            pending.append(row)
        elif "[0] [I] C121_VISIBLE_COST_MONTH " in line:
            row = numeric_fields(line.split("C121_VISIBLE_COST_MONTH ", 1)[1])
            required = ("visible", "month", "calls", "quotes", "quote_ops", "cached_ops", "quote_ticks", "cached_ticks")
            if any(not isinstance(row.get(k), int) or row[k] < 0 for k in required):
                raise ValueError("invalid period cost")
            if row["calls"] < row["quotes"] or row["quotes"] != len(pending):
                raise ValueError("quote count does not reconcile")
            if row["quote_ops"] != sum(q["ops"] for q in pending) or row["quote_ticks"] != sum(q["ticks"] for q in pending):
                raise ValueError("quote costs do not reconcile")
            row["quote_details"] = pending
            pending = []
            periods.append(row)
    if not periods or len({r["month"] for r in periods}) != len(periods):
        raise ValueError("missing or duplicate closed periods")
    if len({r["visible"] for r in periods}) != 1:
        raise ValueError("intervention changed during cost trace")
    return periods, pending


def analyse(folder):
    folder = Path(folder)
    report = json.loads((folder / "report.json").read_text(encoding="utf8"))
    if not report["pass"] or not all(report["checks"].values()):
        raise ValueError("unhealthy or unexposed mechanism")
    path = folder / "engine.log"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != report["log_sha256"]:
        raise ValueError("engine log changed")
    periods, pending = decode_cost(raw.decode("utf8"))
    selected = [r for r in periods if 1970*12+1 <= r["month"] <= 1972*12+12]
    if [r["month"] for r in selected] != list(range(1970*12+1, 1972*12+13)):
        raise ValueError("three-year accounting sequence incomplete")
    quotes = [q for r in selected for q in r["quote_details"]]
    costs = sorted(q["ops"] for q in quotes)
    calls = sum(r["calls"] for r in selected)
    cached = calls-len(quotes)
    cached_ops = sum(r["cached_ops"] for r in selected)
    return {"kind": "natural_fleet_call_cost_not_matched_input_optimization",
            "folder": str(folder), "visible": selected[0]["visible"],
            "log_sha256": digest, "plan_sha256": hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest(),
            "periods": selected, "calls": calls, "full_quotes": len(quotes),
            "quote_ops": sum(costs), "cached_calls": cached, "cached_ops": cached_ops,
            "ops_per_full_quote_mean": sum(costs)/len(costs) if costs else None,
            "ops_per_full_quote_median": median(costs) if costs else None,
            "ops_per_full_quote_p95": costs[math.ceil(len(costs)*0.95)-1] if costs else None,
            "ops_per_cached_or_noop_call": cached_ops/cached if cached else None,
            "quote_ticks": sum(r["quote_ticks"] for r in selected),
            "cached_ticks": sum(r["cached_ticks"] for r in selected),
            "max_month_ops": max(r["quote_ops"]+r["cached_ops"] for r in selected),
            "quotes_in_unclosed_period": len(pending),
            "adoption": False, "economic_verdict": "not_evaluated",
            "limitation": "includes cost of the actual quote body; excludes instrumentation wrapper and logging, month labels follow scheduler entry"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    reports = [analyse(folder) for folder in args.folders]
    result = {"reports": reports, "decoder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps([{k: v for k, v in r.items() if k != "periods"} for r in reports], indent=2))
