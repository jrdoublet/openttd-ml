"""Decode passive station balances: lower bounds only, no adoption verdict."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from analyse_c121_pax_flux import numeric_fields
from c121_station_flux_estimator import station_arrivals


def decode_balance(fields):
    required = ("station", "cargo", "start_date", "end_date", "period_days",
                "pickups_lower", "queue_start", "queue_end", "qualified_bound",
                "risk_samples", "skew_samples", "samples", "max_gap", "lower_pm", "exact_pm", "losses")
    if any(not isinstance(fields.get(k), (int, float)) or not math.isfinite(fields[k]) for k in required):
        return {"status": "unknown", "reason": "missing_or_invalid_field", "monthly": None}
    if (fields["end_date"] - fields["start_date"] != fields["period_days"]
            or fields["period_days"] <= 0 or fields["samples"] < 1
            or fields["losses"] != -1 or fields["exact_pm"] != -1):
        return {"status": "unknown", "reason": "inconsistent_contract", "monthly": None}
    if fields["qualified_bound"] != 1 or fields["risk_samples"] != 0 or fields["skew_samples"] != 0:
        return {"status": "unknown", "reason": "unsafe_or_incoherent", "monthly": None}
    result = station_arrivals(days=fields["period_days"], pickups=fields["pickups_lower"],
        queue_start=fields["queue_start"], queue_end=fields["queue_end"], losses=None)
    bound = result["lower_bound_monthly"]
    if bound is None or not math.isclose(fields["lower_pm"], bound, rel_tol=1e-5, abs_tol=1e-4):
        return {"status": "unknown", "reason": "balance_mismatch", "monthly": None}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bench = json.loads(args.bench.read_text(encoding="utf8"))
    manifest = args.bench.with_suffix(".manifest.json")
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == bench["manifest_sha256"]
    rows, hashes = [], {}
    for game in bench["games"]:
        log = args.bench.parent / "bench_engine" / Path(game["engine_log_path"]).name
        hashes[log.name] = hashlib.sha256(log.read_bytes()).hexdigest()
        for line in log.read_text(encoding="utf8").splitlines():
            if "[0] [I]" not in line or "C121_STATION_FLUX " not in line:
                continue
            fields = numeric_fields(line.split("C121_STATION_FLUX ", 1)[1])
            rows.append({"game_id": game["game_id"], "seed": game["seed"],
                "fields": fields, "observation": decode_balance(fields)})
    qualified = [r for r in rows if r["observation"]["status"] == "lower_bound"]
    summary = {"campaign": bench["campaign_id"], "bundle_sha256": bench["source_bundle_sha256"],
        "manifest_sha256": bench["manifest_sha256"], "log_hashes": hashes,
        "games_complete_healthy": all(g["game_ok"] and g["game_status"] == "complete" for g in bench["games"]),
        "windows": len(rows), "status_counts": dict(Counter(r["observation"]["status"] for r in rows)),
        "unknown_reasons": dict(Counter(r["observation"].get("reason") for r in rows if r["observation"]["status"] == "unknown")),
        "qualified_stations": len({(r["game_id"], r["fields"]["station"]) for r in qualified}),
        "positive_bound_windows": sum(r["observation"]["lower_bound_monthly"] > 0 for r in qualified),
        "observed_pickups_lower": sum(r["fields"]["pickups_lower"] for r in rows),
        "qualified_pickups_lower": sum(r["fields"]["pickups_lower"] for r in qualified),
        "exact_demand_windows": 0, "economic_verdict": "not_evaluated", "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("rows", "log_hashes")}, indent=2))


if __name__ == "__main__":
    main()
