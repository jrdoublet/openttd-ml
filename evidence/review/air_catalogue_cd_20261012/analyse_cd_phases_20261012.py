"""Disjoint annual LOOP_OPS and AIR_LIGHT by phase across frozen CD C10/C30 runs.

Cross-tree C66.3 runs: compare paired seeds, not a fictitious common-code C66.4.
"""
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from analyse_ac_loop_opcode import PHASES, logfile_stats, paired_bootstrap_ci


def collect(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf8"))
    assert not data.get("failed_runs") and all(g["game_ok"] for g in data["games"])
    logs = {}
    for game in data["games"]:
        log = path.with_name(path.stem + "_engine") / Path(game["engine_log_path"]).name
        assert log.is_file() and log.stat().st_size > 0
        logs[game["seed"]] = logfile_stats(log)
    return data, logs


def main():
    root = Path(__file__).resolve().parents[1]
    pairs = {}
    annual_raw = {}
    for count in (10, 30):
        ref_run = "r2" if count == 10 else "r1"
        ref_path = root.parent / "cd_baseline_stage_20261012" / "results" / f"cd_baseline_C{count}x4_20261012_{ref_run}.json"
        var_path = root / "results" / f"cd_combined_C{count}x4_20261012_r1.json"
        a, al = collect(ref_path)
        b, bl = collect(var_path)
        assert a["seeds"] == b["seeds"] and a["years"] == b["years"] == 4
        assert len(al) == len(bl) == count
        for seed in a["seeds"]:
            assert seed not in pairs
            aa, bb = al[seed], bl[seed]
            years = ("1970", "1971", "1972")
            assert all(y in aa and y in bb and aa[y]["loop_posts"] and bb[y]["loop_posts"] for y in years)
            row = defaultdict(int)
            annual_raw[str(seed)] = {}
            for year in years:
                annual_raw[str(seed)][year] = {
                    arm: {
                        "loop_executed_ops": content[year]["loop_executed_ops"],
                        "sleep_left_ops": content[year]["sleep_left_ops"],
                        "loop_posts": content[year]["loop_posts"],
                    }
                    for arm, content in (("reference", aa), ("variant", bb))
                }
                row["slices_ref"] += aa[year]["airlight_slices"]
                row["slices_var"] += bb[year]["airlight_slices"]
                for phase in PHASES:
                    row["phase:" + phase] += bb[year]["phase_ops"][phase] - aa[year]["phase_ops"][phase]
                    row["calls:" + phase] += bb[year]["phase_calls"][phase] - aa[year]["phase_calls"][phase]
                for post in set(aa[year]["loop_posts"]) | set(bb[year]["loop_posts"]):
                    if post in ("sleep_left", "_year"):
                        continue
                    row["post:" + post] += (bb[year]["loop_posts"].get(post, {}).get("ops", 0)
                                            - aa[year]["loop_posts"].get(post, {}).get("ops", 0))
                row["global"] += bb[year]["loop_executed_ops"] - aa[year]["loop_executed_ops"]
            assert row["global"] == sum(v for k, v in row.items() if k.startswith("post:"))
            pairs[seed] = dict(row)
    assert len(pairs) == 40
    result = {"valid": True, "pairs": len(pairs), "closed_years": [1970, 1971, 1972], "posts": {}, "air_phases": {}, "phase_calls": {}}
    phase_coverage = sum(p["slices_ref"] for p in pairs.values()) > 0 and sum(p["slices_var"] for p in pairs.values()) > 0
    result["air_light_coverage"] = {"measured": phase_coverage,
        "ref_slices": sum(p["slices_ref"] for p in pairs.values()),
        "var_slices": sum(p["slices_var"] for p in pairs.values())}
    for prefix, group in (("post:", "posts"), ("phase:", "air_phases"), ("calls:", "phase_calls")):
        keys = sorted({k for row in pairs.values() for k in row if k.startswith(prefix)})
        for key in keys:
            values = [row.get(key, 0) for row in pairs.values()]
            result[group][key[len(prefix):]] = {"mean_delta": mean(values),
                "ci95": paired_bootstrap_ci(values, repeats=5000),
                "positive": sum(v > 0 for v in values), "negative": sum(v < 0 for v in values)}
    if not phase_coverage:
        result["air_phases"] = None
        result["phase_calls"] = None
    values = [row["global"] for row in pairs.values()]
    result["global"] = {"mean_delta": mean(values), "ci95": paired_bootstrap_ci(values, repeats=5000)}
    out = root / "results" / "cd_combined_C40x4_20261012_phase_comparison.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    raw_out = root / "results" / "cd_combined_C40x4_20261012_opcode_annual_raw.json"
    raw_out.write_text(json.dumps({
        "scope": "80 frozen engine logs: 40 paired seeds, closed annual LOOP_OPS",
        "complete_years": ["1970", "1971", "1972"],
        "paired": annual_raw,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"global": result["global"], "top_posts": sorted(result["posts"].items(), key=lambda x: -abs(x[1]["mean_delta"]))[:7],
                      "air_phases": result["air_phases"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
