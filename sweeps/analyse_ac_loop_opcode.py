"""Parse per-year LOOP_OPS and AIR_LIGHT from exact paired diagnostic logs.

LOOP_OPS: instrumented annual VM work per disjoint main-loop post, including
spent ticks; excludes sleep_left from executed work. This is broader than H5
but is still not a hardware CPU measurement or whole application CPU.
AIR_LIGHT: sum of per-invocation disjoint AIR phases; don't divide by phase
invocations and call that per-pair opcodes.
"""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import random
import re
from statistics import mean

LOOP = re.compile(r"LOOP_OPS\s+y=(\d+)\s+post=(\S+)\s+n=(\d+)\s+ops=(\d+)\s+tk=(\d+)")
LIGHT = re.compile(r"AIR_LIGHT v=1 .*\bedge=exit\b(.*)")
FIELD = re.compile(r"(\w+)=([^\s]+)")
PHASES = ("prepare", "sites", "new_pairs", "hub_discover", "hub_site", "hub_hub", "finalize")


def paired_bootstrap_ci(values, repeats=20000):
    if not values:
        return None
    rng = random.Random(0)
    n = len(values)
    samples = sorted(
        sum(values[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(repeats)
    )
    return [samples[int(0.025 * (repeats - 1))], samples[int(0.975 * (repeats - 1))]]


def logfile_stats(path):
    by_year = defaultdict(lambda: {
        "loop_posts": {}, "loop_executed_ops": 0, "sleep_left_ops": 0,
        "phase_ops": {phase: 0 for phase in PHASES},
        "phase_calls": {phase: 0 for phase in PHASES},
        "airlight_slices": 0,
    })
    with Path(path).open(encoding="utf-8", errors="replace") as source:
        for line in source:
            l = LOOP.search(line)
            if l:
                year, post, n, ops, ticks = l.groups()
                row = by_year[int(year)]
                # exactly one annual dump per year per game
                entry = row["loop_posts"].setdefault(post, {"n": 0, "ops": 0, "ticks": 0})
                entry["n"] += int(n)
                entry["ops"] += int(ops)
                entry["ticks"] += int(ticks)
                if post == "sleep_left":
                    row["sleep_left_ops"] += int(ops)
                elif post != "_year":
                    row["loop_executed_ops"] += int(ops)
                continue
            a = LIGHT.search(line)
            if not a:
                continue
            date = re.search(r"\bOPEX (\d{4})-", line)
            if not date:
                continue
            year = int(date.group(1))
            row = by_year[year]
            fields = dict(FIELD.findall(a.group(1)))
            row["airlight_slices"] += 1
            for phase in PHASES:
                row["phase_ops"][phase] += int(fields.get(phase + "_ops", 0))
                row["phase_calls"][phase] += int(fields.get(phase + "_calls", 0))
    return {str(y): data for y, data in sorted(by_year.items())}


def analyse(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    path = Path(path)
    bench = "policies" in d
    policy_ids = [p["id"] for p in d["policies"]] if bench else ["reference", "variant"]
    if len(policy_ids) != 2:
        raise ValueError("exactly two policy IDs are required")

    def host_log(p):
        if p is None:
            raise ValueError("game without engine log")
        raw = str(p).replace("\\", "/")
        if raw.startswith("/work/"):
            return path.parent.parent / raw[len("/work/"):]
        return Path(p)

    logs = {}
    for game in d["games"]:
        arm = game["policy_id"] if bench else game["arm"]
        key = f"{arm}:{game['seed']}"
        logs[key] = logfile_stats(host_log(
            game.get("engine_log_path") if bench else game.get("log_path")))
    if bench:
        valid = (not d.get("failed_runs")
                 and len(d["games"]) == 2 * len(d["seeds"])
                 and all(bool(g.get("game_ok")) for g in d["games"])
                 and all(g.get("source_bundle_sha256") == d.get("source_bundle_sha256")
                         for g in d["games"]))
    else:
        valid = bool(d.get("complete")) and bool(d.get("sources_unchanged"))
    paired = {}
    for seed in d["seeds"]:
        off = logs.get(f"{policy_ids[0]}:{seed}", {})
        on = logs.get(f"{policy_ids[1]}:{seed}", {})
        common = sorted(set(off).intersection(on))
        # exclude right-censored final year if annual LOOP_OPS flush not emitted
        common = [y for y in common if off[y]["loop_posts"] and on[y]["loop_posts"]]
        paired[str(seed)] = {}
        for year in common:
            a, b = on[year], off[year]
            paired[str(seed)][year] = {
                "loop_executed_ops_delta": a["loop_executed_ops"] - b["loop_executed_ops"],
                "loop_executed_ops_ref": b["loop_executed_ops"],
                "sleep_left_ops_delta": a["sleep_left_ops"] - b["sleep_left_ops"],
                "loop_post_deltas": {
                    post: a["loop_posts"].get(post, {}).get("ops", 0)
                        - b["loop_posts"].get(post, {}).get("ops", 0)
                    for post in sorted(set(a["loop_posts"]) | set(b["loop_posts"]))
                    if post not in ("_year", "sleep_left")
                },
                "air_phase_deltas": {
                    phase: a["phase_ops"][phase] - b["phase_ops"][phase]
                    for phase in PHASES
                },
                "air_phase_calls_deltas": {
                    phase: a["phase_calls"][phase] - b["phase_calls"][phase]
                    for phase in PHASES
                },
            }
    # LOOP_OPS flushes at the NEXT calendar-year boundary; the terminal
    # checkpoint in a 3-year duel does not guarantee a 1972 annual flush.
    # Only use years that contain complete, comparable LOOP_OPS in EVERY arm.
    all_requested_years = [str(y) for y in range(1970, 1970 + int(d["years"]))]
    complete_years = [
        year for year in all_requested_years
        if all(year in paired[str(seed)] for seed in d["seeds"])
    ]
    final_year = complete_years[-1] if complete_years else None
    aligned = [paired[str(seed)].get(final_year) for seed in d["seeds"]]
    aligned = [a for a in aligned if a]
    full_seed_deltas = []
    full_seed_reference = []
    for seed in d["seeds"]:
        per_year = paired[str(seed)]
        if all(year in per_year for year in complete_years):
            full_seed_deltas.append(sum(per_year[year]["loop_executed_ops_delta"]
                                        for year in complete_years))
            full_seed_reference.append(sum(per_year[year]["loop_executed_ops_ref"]
                                           for year in complete_years))
    return {
        "source": str(path), "valid": valid,
        "source_frozen": bool(bench or d.get("source_frozen")),
        "seeds": d["seeds"], "years": d["years"],
        "final_year": final_year, "final_year_paired_count": len(aligned),
        "observed_complete_years": complete_years,
        "terminal_year_unflushed": str(1970 + int(d["years"]) - 1) not in complete_years,
        "mean_final_year_loop_executed_ops_delta":
            mean(a["loop_executed_ops_delta"] for a in aligned) if aligned else None,
        "whole_horizon_paired": len(full_seed_deltas),
        "whole_horizon_mean_loop_delta": mean(full_seed_deltas) if full_seed_deltas else None,
        "whole_horizon_mean_reference": mean(full_seed_reference) if full_seed_reference else None,
        "whole_horizon_ratio_of_means": (
            1 + mean(full_seed_deltas) / mean(full_seed_reference)
            if full_seed_reference and mean(full_seed_reference) > 0 else None
        ),
        "whole_horizon_bootstrap_95_ci": paired_bootstrap_ci(full_seed_deltas),
        "whole_horizon_pos_neg_tie": {
            "positive": sum(v > 0 for v in full_seed_deltas),
            "negative": sum(v < 0 for v in full_seed_deltas),
            "equal": sum(v == 0 for v in full_seed_deltas),
        },
        "per_game_annual": logs, "paired": paired,
        "caveat": "tick-based disjoint AI main-loop posts, not whole hardware CPU; LOOP_OPS flushes once per year, so terminal year can be right-censored; only observed_complete_years are counted; benchmarks are frozen when source_frozen true",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.result)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("valid", "final_year_paired_count",
                       "mean_final_year_loop_executed_ops_delta",
                       "whole_horizon_paired", "whole_horizon_mean_loop_delta",
                       "whole_horizon_ratio_of_means", "whole_horizon_bootstrap_95_ci")}))
