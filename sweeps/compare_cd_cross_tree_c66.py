"""Compare TWO sequential C66.3 mono-policy runs from independent source trees.

Never attempt to load two copies both called OpexAI within one OpenTTDLab
run_experiments call: that API indexes copies by the AI name.
This script checks the common adversary/config/dependencies, while expecting
OpexAI source fingerprints to differ. It reports paired economics and
disjoint annual LOOP_OPS, without inventing a C66.4 common-bundle verdict.
"""

import argparse
import json
import random
from pathlib import Path
from statistics import mean, median

if __package__:
    from .analyse_ac_loop_opcode import logfile_stats
else:
    from analyse_ac_loop_opcode import logfile_stats


def ci(values, n=10000):
    rng = random.Random(20261012)
    size = len(values)
    dist = sorted(sum(values[rng.randrange(size)] for _ in range(size)) / size
                  for _ in range(n))
    return [dist[int((n - 1) * 0.025)], dist[int((n - 1) * 0.975)]]


def collect(result_path, opcode=True):
    result_path = Path(result_path).resolve()
    data = json.loads(result_path.read_text(encoding="utf-8"))
    manifest = json.loads(result_path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert len(data["policies"]) == 1, "Expected C66.3, not C66.4"
    assert not data.get("failed_runs")
    assert len(data["games"]) == len(data["seeds"]) * int(data["repeats"])
    assert all(x["game_ok"] for x in data["games"])
    policy = data["policies"][0]["id"]
    records = {}
    for record in data["summary"]:
        if record["arm"] != "OpexAI" or record.get("policy_id") != policy:
            continue
        assert record["horizon_complete"] and record["include_in_economic_stats"]
        assert record["profit_year_coverage"] == "complete"
        key = (record["seed"], record["repeat"])
        assert key not in records
        records[key] = record
    assert len(records) == len(data["games"])
    by_game = {}
    for game in data["games"]:
        key = (game["seed"], game["repeat"])
        if not opcode:
            by_game[key] = {}
            continue
        logpath = str(game["engine_log_path"]).replace("\\", "/")
        if logpath.startswith("/work/"):
            # Source trees are mounted below /work, but results are local to
            # the individual worktree. Only the filename is needed.
            logpath = result_path.with_name(result_path.stem + "_engine") / Path(logpath).name
        else:
            logpath = Path(logpath)
        assert Path(logpath).is_file() and Path(logpath).stat().st_size > 0
        by_game[key] = logfile_stats(logpath)
    assert set(records) == set(by_game)
    return data, manifest, records, by_game


def compare(refpath, varpath, opcode=True):
    ref, rm, rs, ro = collect(refpath, opcode=opcode)
    var, vm, vs, vo = collect(varpath, opcode=opcode)
    assert ref["years"] == var["years"]
    assert ref["seeds"] == var["seeds"]
    assert ref["repeats"] == var["repeats"]
    assert set(rs) == set(vs)
    # Compare actual frozen input fingerprints; never claim source parity.
    assert rm["sources"]["AAAHogEx"]["sha256"] == vm["sources"]["AAAHogEx"]["sha256"]
    assert rm["configuration"]["raw"] == vm["configuration"]["raw"]
    assert rm["versions"] == vm["versions"]
    assert rm["libraries"] == vm["libraries"]
    ref_settings = rm["policies"][0]["settings"]["effective"]
    var_settings = vm["policies"][0]["settings"]["effective"]
    assert ref_settings == var_settings, "Unexpected changed AI setting"
    assert rm["sources"]["OpexAI"]["sha256"] != vm["sources"]["OpexAI"]["sha256"], (
        "No source-tree delta to evaluate")
    keys = sorted(rs)
    result = {
        "valid": True,
        "scope": "two separately frozen C66.3 mono-policy runs, NOT C66.4",
        "n": len(keys),
        "seeds": [k[0] for k in keys],
        "years": ref["years"],
        "source_sha256": {
            "reference": rm["sources"]["OpexAI"]["sha256"],
            "variant": vm["sources"]["OpexAI"]["sha256"],
            "adversary": rm["sources"]["AAAHogEx"]["sha256"],
        },
        "economic": {},
        "opcode": {},
    }
    for metric in ("profit_year", "company_value", "primary_vehicles", "n_stations"):
        diffs = [vs[key][metric] - rs[key][metric] for key in keys]
        reference = [rs[key][metric] for key in keys]
        result["economic"][metric] = {
            "mean_delta": mean(diffs), "median_delta": median(diffs),
            "wins": sum(v > 0 for v in diffs),
            "losses": sum(v < 0 for v in diffs),
            "ties": sum(v == 0 for v in diffs),
            "mean_reference": mean(reference),
            "ratio_of_means": (mean(diffs) / mean(reference)
                               if mean(reference) != 0 else None),
            "bootstrap_95_ci": ci(diffs),
            "by_seed_delta": {str(k[0]): v for k, v in zip(keys, diffs)},
        }
    if not opcode:
        result["opcode"] = {"coverage": "not measured: economic-only with probe_loop_ops=0"}
        return result
    years = [str(1970 + i) for i in range(int(ref["years"]) - 1)]
    # C121 loop counters flush at the NEXT new year, so the last year is censored.
    for key in keys:
        for year in years:
            a = ro[key].get(year)
            b = vo[key].get(year)
            assert a is not None and b is not None
            assert a["loop_posts"] and b["loop_posts"]
            assert a["loop_executed_ops"] > 0 and b["loop_executed_ops"] > 0
    result["opcode"]["complete_years"] = years
    for window in ([years[0], years[1]], years):
        name = f"{window[0]}-{window[-1]}"
        diffs = [sum(vo[key][y]["loop_executed_ops"] - ro[key][y]["loop_executed_ops"]
                     for y in window) for key in keys]
        refs = [sum(ro[key][y]["loop_executed_ops"] for y in window) for key in keys]
        result["opcode"][name] = {
            "mean_delta": mean(diffs),
            "mean_reference": mean(refs),
            "ratio_of_means": mean(diffs) / mean(refs),
            "bootstrap_95_ci": ci(diffs),
            "increases": sum(x > 0 for x in diffs),
            "decreases": sum(x < 0 for x in diffs),
            "by_seed_delta": {str(k[0]): v for k, v in zip(keys, diffs)},
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("variant", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--economic-only", action="store_true",
                        help="Validate economic metrics without inventing LOOP_OPS when probes were OFF")
    args = parser.parse_args()
    result = compare(args.reference, args.variant, opcode=not args.economic_only)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": result["valid"], "n": result["n"],
                      "economic": result["economic"]["profit_year"],
                      "opcodes": {k: v for k, v in result["opcode"].items()
                                  if k != "complete_years"}}, ensure_ascii=False))
