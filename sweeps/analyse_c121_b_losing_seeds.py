"""Offline losing-seed inspection; no games, no causal/economic verdict."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from sweeps.diag_c121_postbuild import parse_fields
from sweeps.inspect_c121_investments import investments, BUILD

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/c121_nuit_20261003_203842/snapshot/results"
CAMPAIGN = "c121_B3_20261004_075644"
SUFFIXES = ["air_hubhub_marginal", "air_first_live_growth_phase_years", "air_project_realization_adaptive"]
OUT = ROOT / "results/c121_adoption_20261004"
OUT.mkdir(exist_ok=True)
report = {}
for suffix in SUFFIXES:
    path = BASE / f"{CAMPAIGN}_{suffix}_B.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = sorted(data["policy_comparison"]["per_pair"],
                   key=lambda p: p["metrics"]["profit_year"]["policy_delta"])
    worst = pairs[:3]
    seeds = {p["seed"] for p in worst}
    rows = {}
    for line in path.with_suffix(".jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        if r["company_slot"] == 0 and r["run"][1] in seeds:
            rows[r["policy_id"], r["run"][1], r["date"]] = r
    strategy = []
    log_hashes = {}
    logs = {}
    for g in data["games"]:
        lp = ROOT / g["engine_log_path"].removeprefix("/work/")
        if suffix == SUFFIXES[-1] or g["seed"] in seeds:
            raw = lp.read_bytes()
            log_hashes[str(lp.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
            t = raw.decode("utf-8", errors="replace")
            logs[g["policy_id"], g["seed"]] = t
            for line in t.splitlines():
                if re.search(r"\[script:\d+\]\s*\[0\].*?\bC121_STRATEGY_LOCK\s+", line):
                    fields = parse_fields(line.split("C121_STRATEGY_LOCK", 1)[1])
                    strategy.append(dict(seed=g["seed"], policy_id=g["policy_id"], **fields))
    cases = []
    for p in worst:
        seed = p["seed"]
        metric = p["metrics"]["profit_year"]
        policies = ("reference", suffix)
        physical = {}
        yearly = {}
        build_counts = {}
        for policy in policies:
            rr = sorted((r for (pol, s, date), r in rows.items() if pol == policy and s == seed),
                        key=lambda r: r["date"])
            terminal = rr[-1]
            physical[policy] = {k: terminal.get(k) for k in (
                "date", "air_primary_vehicles", "air_airports", "air_passenger_capacity",
                "air_engine_counts", "primary_vehicles_by_mode", "money", "current_loan",
                "company_value", "median_station_rating", "months_of_bankruptcy")}
            year_last = {}
            for r in rr:
                year_last[r["date"][:4]] = r
            yearly[policy] = {y: {k: r.get(k) for k in (
                "air_primary_vehicles", "air_airports", "air_passenger_capacity", "money",
                "primary_vehicles_by_mode", "company_value")} for y, r in year_last.items()}
            text = logs[policy, seed]
            builds = [parse_fields(m[1]) for line in text.splitlines() if (m := BUILD.search(line))]
            build_counts[policy] = dict(investments(text),
                arms=dict(Counter(r.get("arm", "unknown") for r in builds)),
                engines=dict(Counter(r.get("engine", "unknown") for r in builds)))
        first = next((date for date in sorted({date for pol,s,date in rows if s==seed})
                      if rows.get(("reference", seed, date), {}).get("air_primary_vehicles")
                      != rows.get((suffix, seed, date), {}).get("air_primary_vehicles")), None)
        cases.append(dict(seed=seed, profit_year=metric,
            loss_pct=100*metric["policy_delta"]/metric["reference_opex"],
            value=p["metrics"]["company_value"], annual=p["annual_trajectory"],
            terminal_physical=physical, yearly_physical=yearly,
            first_air_fleet_count_difference=first, builds=build_counts))
    report[suffix] = dict(result_path=str(path.relative_to(ROOT)),
        result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        jsonl_sha256=hashlib.sha256(path.with_suffix(".jsonl").read_bytes()).hexdigest(),
        bundle=data["source_bundle_sha256"], cases=cases,
        strategy_locks=strategy, inspected_log_hashes=log_hashes)
out = OUT / "losing_seeds.json"
if out.exists():
    raise FileExistsError(out)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
for suffix, data in report.items():
    print(suffix)
    for c in data["cases"]:
        print(c["seed"], round(c["loss_pct"],2), c["profit_year"]["policy_delta"],
              "first_fleet_diff",c["first_air_fleet_count_difference"])
        for policy, r in c["terminal_physical"].items():
            print(policy, "air",r["air_primary_vehicles"],"airports",r["air_airports"],
                  "pax",r["air_passenger_capacity"],"modes",r["primary_vehicles_by_mode"],
                  "cash",r["money"], "builds", c["builds"][policy]["arms"])
    if data["strategy_locks"]:
        print("locks",Counter(r.get("regime") for r in data["strategy_locks"]))
print(out)
