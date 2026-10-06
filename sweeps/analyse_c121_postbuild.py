"""Recover/analyse retained post-build checkpoints without running any game.

The interrupted run remains interrupted; this writes a separate offline receipt.
All original source hashes and copied inputs must match. Added analysis files are
listed separately, never presented as having existed in the original manifest.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import statistics

from . import diag_c121_postbuild as diag


def annual_key_fix(row):
    row["annual"] = {name: {int(k): v for k, v in values.items()} for name, values in row["annual"].items()}
    return row


def checkpoint_coverage(rows, arm, seed, years):
    expected = [f"{1970 + m // 12:04d}-{m % 12 + 1:02d}-01" for m in range(years * 12 + 2)]
    return (sorted(r["date"] for r in rows) == expected
            and all(r["arm"] == arm and r["seed"] == seed for r in rows))


def perturbation(games, model, seeds, years, duel):
    pair = [{**g, "arm": "reference" if g["arm"] == model else "trace"}
            for g in games if g["arm"] in (model, model + "_trace")]
    result = duel.compare(pair, ["reference", "trace"], seeds, years)
    if not result["complete"]:
        return {"complete": False, "practical_filter": False}
    delta = result["paired_final"]["trace"]
    ref = statistics.mean(g["annual"]["OpexAI"][years - 1] for g in games if g["arm"] == model)
    profit_pct = 100 * delta["opex_profit_delta"] / ref if ref > 0 else None
    nonnegative = sum(p["opex_profit_delta"] >= 0 for p in delta["per_seed"])
    return {"complete": True, **delta, "profit_delta_pct": profit_pct, "nonnegative_seeds": nonnegative,
            "profit_delta_median": statistics.median(p["opex_profit_delta"] for p in delta["per_seed"]),
            "practical_filter": profit_pct is not None and profit_pct >= -5
                and delta["value_delta_pct"] is not None and delta["value_delta_pct"] >= -5 and nonnegative >= 3,
            "neutrality_proven": False}


def recover(folder, out):
    import diag_cadence_duel as duel
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    years, seeds, names = plan["years"], plan["seeds"], plan["arms"]
    if out.exists():
        raise FileExistsError(out)
    games, audits, inputs, metrics, coverage, logs = [], {}, {}, {}, {}, {}
    for seed in seeds:
        for name in names:
            key = f"{name}_{seed}"
            log_path, rows_path = folder / f"{key}.log", folder / f"{key}.jsonl"
            for path in (log_path, rows_path):
                inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            rows = [annual_key_fix(json.loads(line)) for line in rows_path.read_text(encoding="utf-8").splitlines()]
            if any(r["arm"] != name or r["seed"] != seed for r in rows):
                raise ValueError("Mixed identities in checkpoints")
            coverage[key] = checkpoint_coverage(rows, name, seed, years)
            for row in rows:
                row["log_path"] = str(log_path)
            games.append(duel.finish_game(rows, years))
            logs[name, seed] = log_path.read_text(encoding="utf-8")
            if name.endswith("_trace"):
                a = diag.audit(log_path.read_text(encoding="utf-8"))
                audits[key] = a
                grouped = defaultdict(list)
                for w in a["windows"]:
                    year = (date(1, 1, 1) + timedelta(days=w["day"] - 366)).year
                    grouped[year, w["kind"]].append(w)
                metrics[key] = {
                    "phases_by_year": [
                        {"year": year, "kind": kind, "n": len(ws), "ops_sum": sum(w["ops"] for w in ws),
                         "days_sum": sum(w["days"] for w in ws),
                         "days_median": statistics.median(w["days"] for w in ws),
                         "days_max": max(w["days"] for w in ws),
                         **{unit: diag.distribution(w[unit] for w in ws) for unit in ("days", "ticks", "ops")}}
                        for (year, kind), ws in sorted(grouped.items())],
                    "gap_summary": a["gap_summary"], "counts": a["counts"],
                    "issues": dict(Counter(i["reason"] for i in a["issues"])),
                    "stops": dict(Counter(s["fields"].get("reason") for s in a["stops"])),
                    "kpass_financeable_at_stop": sum(s["fields"].get("reason") == "k_pass"
                                                      and s["financeable_at_stop"] is True for s in a["stops"]),
                }
    current = duel.source_hashes(diag.ROOT)
    original = plan["source_hashes"]
    changed = [name for name, value in original.items() if current.get(name) != value]
    additions = sorted(set(current) - set(original))
    identity = diag.probe_identity(logs)
    checks = {
        "probe_identity": identity["pass"],
        "monthly_coverage": all(coverage.values()),
        "all_games": len(games) == len(seeds) * len(names) and all(g["valid"] for g in games),
        "original_sources_unchanged": not changed,
        "executed_copies_unchanged": diag.tree_hashes(folder / "copies") == plan["executed_copy_hashes"],
        "fixture_unchanged": hashlib.sha256((diag.ROOT / "tests/mechanisms/c121_postbuild_probe.nut").read_bytes()).hexdigest() == plan["fixture_sha256"],
        "trace_integrity": all(all(i["reason"].startswith("censored_") for i in a["issues"]) for a in audits.values()),
        "exposure": len(audits) == len(seeds) * 2 and all(
            a["counts"].get("outcome", 0) and any(w["kind"] != "fleet" for w in a["windows"]) for a in audits.values()),
    }
    perturb = ({model: perturbation(games, model, seeds, years, duel) for model in diag.BASE_SETTINGS}
               if all(checks.values()) else {"valid": False, "reason": "recovery_checks_failed"})
    untraced = [{**g, "arm": "reference" if g["arm"] == "c115" else "c121"}
                for g in games if g["arm"] in ("c115", "c121")]
    comparison = (duel.compare(untraced, ["reference", "c121"], seeds, years)
                  if all(checks.values()) else {"complete": False, "reason": "recovery_checks_failed"})
    summary = {"checks": checks, "artifact_validation_pass": all(checks.values()),
               "process_status": "interrupted_before_final_report", "recovery": "offline_no_rerun",
               "input_hashes": inputs, "changed_original_sources": changed, "added_files_since_run": additions,
               "perturbation": perturb, "untraced_comparison": comparison, "metrics": metrics,
               "probe_identity": identity,
               "games": games, "audits": audits, "economic_verdict": "not_adoption",
               "checkpoint_coverage": coverage,
               "recovery_reader_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "plan_sha256": hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest()}
    diag.write_new(out, summary)
    print(json.dumps({"checks": checks, "perturbation": perturb,
                      "untraced_comparison": comparison, "metrics": metrics}, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    recover(args.input.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()