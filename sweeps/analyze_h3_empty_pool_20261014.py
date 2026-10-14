"""Read-only forensic audit of V166-policy incremental empty pools in H3.

This does not infer an opportunity, a constructible project, or a causal gain
from a zero candidate count or from idle capital. It never runs OpenTTD.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date as Date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT.parent
H3 = RESULTS / "scores_p2_p4_signed_hub_stage_20261014" / "results"
BASE = RESULTS / "scores_p2_p4_save_baseline_stage_20261013" / "results"
ENGINE = H3 / "p2_p4_signed_hub_dev5x5_20261014_engine"
FORK = RESULTS / "scores_p2_p4_net_revenue_stage_20261014" / "results" / "p2_net_savefork_314159_terminal49m_20261014"
ARMS = ("hub_shadow_historical", "hub_signed_positive")
SEEDS = (42, 100, 999, 1234, 5678)
POOL = re.compile(r"\[PORTFOLIO_CACHE\] incremental: candidates=(\d+) od=(\d+) selected=(\d+) remaining=(\d+)")
HUB = re.compile(r"C121_HUB_SIGNED exposure_year=(\d+) quote_evaluations=(\d+) positive_quotes=(\d+) max_gain_annual=(\d+) applied=(\d+)")
LOG_DATE = re.compile(r"\bOPEX (19\d\d)-(\d\d?)-(\d\d?)\b")
LINE_DATE = re.compile(r"\] \[I\] (19\d\d)-(\d\d?)-(\d\d?)\b")
PHYSICAL = re.compile(r"(?:C121_BUILD line=(\d+) arm=([a-z]+)|\[FLEET_PROJECT\] line=(\d+) added=(\d+))")


def extract(path: Path, threshold: int = 100_000) -> dict:
    """For each row keep its line and latest explicit OpexAI game date.

    A reported date is an approximation for undated cache rows. Do not use
    this to certify the VM tick at which an investment was available.
    """
    events = []
    hubs = []
    builds = []
    date = None
    last_physical = None
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = LOG_DATE.search(line) or LINE_DATE.search(line)
        if m:
            date = f"{m.group(1)}-{int(m.group(2)):02}-{int(m.group(3)):02}"
        physical = PHYSICAL.search(line)
        if physical:
            last_physical = {"line": lineno, "kind": "air_build" if physical.group(1) else "fleet_add",
                             "line_id": int(physical.group(1) or physical.group(3)),
                             "arm": physical.group(2) if physical.group(1) else None,
                             "last_logged_game_date": date}
            builds.append(last_physical)
        q = POOL.search(line)
        if q:
            candidates, od, selected, remaining = map(int, q.groups())
            events.append({"line": lineno, "last_logged_game_date": date,
                           "candidates": candidates, "od": od,
                           "selected": selected, "capital_remaining": remaining,
                           "preceding_physical": ({**last_physical, "lines_before": lineno-last_physical["line"]}
                                                  if last_physical else None)})
        h = HUB.search(line)
        if h:
            year, quotes, positive, maximum, applied = map(int, h.groups())
            hubs.append({"line": lineno, "exposure_year": year, "quotes": quotes,
                         "positive_quotes": positive, "maximum_model_gain": maximum,
                         "applied": applied})
    high = [e for e in events if e["candidates"] == 0 and e["selected"] == 0
            and e["capital_remaining"] >= threshold]
    for row in high:
        following = next((b for b in builds if b["line"] > row["line"]), None)
        if following is not None:
            row["next_physical"] = {**following, "lines_after": following["line"] - row["line"]}
            d0 = row["last_logged_game_date"]
            d1 = following["last_logged_game_date"]
            row["approx_days_to_next_physical"] = (Date.fromisoformat(d1) - Date.fromisoformat(d0)).days if d0 and d1 else None
        else:
            row["next_physical"] = None
            row["approx_days_to_next_physical"] = None
    return {"pool_snapshots": len(events),
            "zero_candidate_snapshots": sum(e["candidates"] == 0 for e in events),
            "zero_pool_capital_ge_threshold": len(high),
            "high_capital_events": high,
            "hub_annual_reports": hubs,
            "first_nonzero_hub_quote_year": next(
                (h["exposure_year"] for h in hubs if h["positive_quotes"] > 0), None),
            "all_pool_rows": events}


def baseline_months(path: Path) -> dict:
    runs = {}
    missing_logs = set()
    with path.open(encoding="utf-8") as handle:
      for line in handle:
        row = json.loads(line)
        k = tuple(row["run"])
        runs.setdefault(str(k), []).append(row["date"])
        log = row.get("engine_log_path")
        if log:
            name = Path(log.replace("\\", "/")).name
            if not (path.parent / (path.stem.replace(".jsonl", "") + "_engine") / name).is_file():
                missing_logs.add(name)
    return {"run_month_rows": {k: len(v) for k, v in runs.items()},
            "referenced_engine_logs_not_preserved": sorted(missing_logs)}


def last_fork_state() -> dict:
    """Inspect a completed single-arm 49-month replay; never assert A/B gain."""
    manifest = json.loads((FORK / "fork.json").read_text(encoding="utf-8"))
    completed = {}
    for branch in manifest["branches"]:
        file = FORK / "replays" / branch / "replay.json"
        if not file.exists():
            continue
        data = json.loads(file.read_text(encoding="utf-8"))
        row = data["rows"][-1]
        completed[branch] = {"rows": len(data["rows"]), "last_date": row["date"],
                             "dedicated": data["dedicated_network_server"],
                             "unexpected_companies": row["unexpected_companies"],
                             "load_reconcile_seen": data["load_reconcile_seen"],
                             "terminal_checkpoint_observed": data["terminal_checkpoint_observed"],
                             "script_failures": data["script_failures"],
                             "opex_terminal": row["economic_accounts"]["0"]}
    return {"manifest_branches": manifest["branches"], "complete_replays_present": completed,
            "original_snapshot_date": manifest["snapshot"]["calendar_date"],
            "same_historical_tick": manifest["scope"] != "MONTHLY_CHECKPOINT_NOT_C77_TICK",
            "historical_source_exact": manifest["frozen_source_matches"]["reference"]["exact"],
            "historical_source_mismatches": manifest["frozen_source_matches"]["reference"]["mismatches"],
            "paired_comparison_possible": len(completed) == len(manifest["branches"])}


def report(threshold: int = 100_000) -> dict:
    by_seed = {}
    for seed in SEEDS:
        arms = {}
        for arm in ARMS:
            log = ENGINE / f"{arm}_seed{seed}_r0.log"
            arms[arm] = extract(log, threshold)
        a, b = (arms[x]["all_pool_rows"] for x in ARMS)
        first = next((i for i, (x, y) in enumerate(zip(a, b))
                      if (x["candidates"], x["od"], x["selected"], x["capital_remaining"])
                      != (y["candidates"], y["od"], y["selected"], y["capital_remaining"])), None)
        by_seed[str(seed)] = {"arms": arms, "first_cache_sequence_mismatch_index_zero_based": first,
                             "first_cache_sequence_mismatch_rows":
                             None if first is None else {ARMS[0]: a[first], ARMS[1]: b[first]}}
        for arm in ARMS:
            del arms[arm]["all_pool_rows"]
    old = BASE / "scores_p2_p4_v166_physical_base2x5_r2_20261013.jsonl"
    return {"claim": "descriptive_only_not_same_tick_not_marginal",
            "source_version": "7ecbabe8ff4154dfd62184a5d6d1e33db3bbccbf",
            "capital_threshold": threshold, "seed_results": by_seed,
            "v166_physical_base": baseline_months(old),
            "recovered_recent_49m_benchmark": last_fork_state(),
            "limitations": [
                "cache candidates=0 means no survivors/injections after an incremental pass, not absence of all feasible projects",
                "H3 OFF has the V166 economic policy but additional H3 shadow instrumentation; it is not an untouched default V166 run",
                "cached capital remaining is after reserve and after funded projects, not proof any challenger is viable",
                "annual hub exposure is not the date of the first credit/decision and cache index mismatch is not a causal first divergence",
                "V166 physical monthly JSONL does not supply the exact candidateGroups or VM tick of a rejected head",
            ]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    r = report()
    if args.out is not None:
        target = args.out.resolve()
        dest = (ROOT / "results").resolve()
        if dest not in target.parents or target.exists():
            raise SystemExit("Output must be new file under this stage's results directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"threshold": r["capital_threshold"],
                      "high_empty_by_seed": {s: {a: x["zero_pool_capital_ge_threshold"]
                                                      for a, x in data["arms"].items()}
                                             for s, data in r["seed_results"].items()},
                      "v166_missing_logs": len(r["v166_physical_base"]["referenced_engine_logs_not_preserved"])},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
