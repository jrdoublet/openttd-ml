"""Audit exact captured-cargo intervals and exploratory annual forecasts.

Future labels cover observed exact intervals ONLY, never imputed missing months.
Rolling supply is an external oracle benchmark, not a NoAI-accessible feature.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from analyse_c121_pax_flux import numeric_fields
from station_supply import supply_intervals


def rate(rows):
    days = sum(r["period_days"] for r in rows)
    return sum(r["arrivals"] for r in rows) * 30.4 / days if days else None


def metrics(cases, predictor):
    denominator = sum(c["actual"] for c in cases)
    if not cases or denominator <= 0:
        return {"n": len(cases), "wape": None, "bias_pct": None}
    errors = [c[predictor] - c["actual"] for c in cases]
    return {"n": len(cases), "wape": sum(abs(e) for e in errors) / denominator,
            "bias_pct": 100 * sum(errors) / denominator,
            "stations": len({(c["game_id"], c["station"]) for c in cases}),
            "seeds": sorted({c["seed"] for c in cases})}


def analyse(bench_path):
    bench = json.loads(bench_path.read_text(encoding="utf8"))
    manifest_path = bench_path.with_suffix(".manifest.json")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != bench["manifest_sha256"]:
        raise ValueError("manifest hash mismatch")
    if not bench.get("station_supply_telemetry"):
        raise ValueError("station supply telemetry absent")
    checkpoint = bench_path.with_suffix(".jsonl")
    grouped = defaultdict(list)
    for text in checkpoint.read_text(encoding="utf8").splitlines():
        row = json.loads(text)
        if (row.get("source_bundle_sha256") is not None
                and row["source_bundle_sha256"] != bench["source_bundle_sha256"]):
            raise ValueError("checkpoint bundle mismatch")
        if row["company_slot"] == 0:
            grouped[row["game_id"]].append(row)
    windows, cases, excluded, log_hashes = [], [], Counter(), {}
    for game in bench["games"]:
        game_id, seed = game["game_id"], game["seed"]
        rows = sorted(grouped[game_id], key=lambda r: r["date"])
        if not rows or game.get("expected_last_checkpoint", rows[-1]["date"]) not in {r["date"] for r in rows}:
            raise ValueError("checkpoint horizon incomplete")
        if len({r["date"] for r in rows}) != len(rows):
            raise ValueError("duplicate checkpoint date")
        log = bench_path.parent / "bench_engine" / Path(game["engine_log_path"]).name
        log_hashes[log.name] = hashlib.sha256(log.read_bytes()).hexdigest()
        text = log.read_text(encoding="utf8")
        # Runtime cargo labels from the frozen opponent, not assumed numeric IDs.
        cargo_ids = {int(m) for m in re.findall(r"\[1\] \[I\].*?\bid:(\d+) .*?label:PASS\b", text)}
        if len(cargo_ids) != 1:
            raise ValueError("PASS cargo identity not unique in runtime log")
        cargo_id = cargo_ids.pop()
        builds = {}
        for line in text.splitlines():
            if "[0] [I] C121_BUILD " not in line:
                continue
            f = numeric_fields(line.split("C121_BUILD ", 1)[1])
            # Fresh pairs only: no undocumented own-station sharing in proxy.
            if f.get("new_airports") != 2:
                continue
            for end in ("a", "b"):
                station = f.get("station_id_" + end)
                raw = f.get("pax_raw_" + end)
                target_rating = f.get("rating_pax_" + end)
                if (isinstance(station, int) and isinstance(raw, (int, float))
                        and raw >= 0 and isinstance(target_rating, (int, float))
                        and 0 <= target_rating <= 255):
                    builds.setdefault(station, {"raw": raw, "rating": target_rating,
                                                "proxy": raw * (target_rating + 1) / 256})
        by_station, ratings = defaultdict(list), defaultdict(dict)
        for row in rows:
            month = date.fromisoformat(row["date"]).year * 12 + date.fromisoformat(row["date"]).month
            for line in (row.get("line_telemetry") or {}).get("lines", []):
                for endpoint in line.get("endpoint_cargo_stats", []):
                    good = endpoint.get("cargo", {}).get(str(cargo_id), {})
                    if good.get("rated") and isinstance(good.get("rating"), (int, float)):
                        ratings[endpoint["station_id"]][month] = good["rating"]
        for a, b in zip(rows, rows[1:]):
            for w in supply_intervals(a["station_supply"], b["station_supply"]):
                w.update(game_id=game_id, seed=seed, start_checkpoint=a["date"], end_checkpoint=b["date"])
                windows.append(w)
                if w.get("cargo") == cargo_id and w["exact"]:
                    month = date.fromisoformat(a["date"]).year * 12 + date.fromisoformat(a["date"]).month
                    w["month"] = month
                    by_station[w["station"]].append(w)
        for station, build in builds.items():
            available = by_station[station]
            for year in range(1972, 1980):
                anchor = year * 12 + 1
                past = [w for w in available if anchor - 12 <= w["month"] < anchor]
                future = [w for w in available if anchor <= w["month"] < anchor + 12]
                if len(past) < 8 or len(future) < 8:
                    excluded["less_than_8_exact_months_in_past_or_future"] += 1
                    continue
                observed_ratings = [v for m, v in ratings[station].items() if anchor - 12 <= m < anchor]
                if len(observed_ratings) < 8:
                    excluded["missing_past_ratings"] += 1
                    continue
                cases.append({"game_id": game_id, "seed": seed, "station": station, "anchor_year": year,
                              "past_months": len(past), "future_months": len(future),
                              "past_days": sum(w["period_days"] for w in past),
                              "future_days": sum(w["period_days"] for w in future),
                              "actual": rate(future), "initial_offered_proxy": build["proxy"],
                              "past_rating_proxy": build["raw"] * (sum(observed_ratings) / len(observed_ratings) + 1) / 256,
                              "past_supply_oracle": rate(past)})
    holdout = [c for c in cases if c["seed"] in (73, 314, 512)]
    training = [c for c in cases if c["seed"] not in (73, 314, 512)]
    fields = ("initial_offered_proxy", "past_rating_proxy", "past_supply_oracle")
    return {"campaign": bench["campaign_id"], "bundle_sha256": bench["source_bundle_sha256"],
            "manifest_sha256": bench["manifest_sha256"],
            "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "log_hashes": log_hashes,
            "healthy_complete": bool(bench["games"]) and all(g["game_ok"] and g["game_status"] == "complete" for g in bench["games"]),
            "windows": len(windows), "exact_windows": sum(w["exact"] for w in windows),
            "unknown_reasons": dict(Counter(w["reason"] for w in windows if not w["exact"])),
            "forecasts": {"status": "exploratory_partial_year_labels", "excluded": dict(excluded),
                          "strict_12_past_plus_12_future_cases": sum(c["past_months"] == 12 and c["future_months"] == 12 for c in cases),
                          "training": {f: metrics(training, f) for f in fields},
                          "holdout": {f: metrics(holdout, f) for f in fields}},
            "economic_verdict": "not_evaluated", "rows": windows, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bench", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.bench)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "cases", "log_hashes")}, indent=2))


if __name__ == "__main__":
    main()
