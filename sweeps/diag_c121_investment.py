"""Copy-only C121 investment attribution and probe-perturbation diagnostic.

The production AI is never instrumented.  Each arm is loaded by a separate
OpenTTDLab invocation because local_folder sources share the public AI name.
This is a mechanism diagnostic, never an adoption benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from harness import parse_fields
from run_mechanism_fixtures import replace_once, tree_hashes
from diag_r1_r3_mechanisms import new_directory, write_new
from diag_c121_postbuild import run_isolated_arms

SETTINGS = (("c121_air_economics", 1), ("c121_catalog_incremental", 1))
SPEC = "OpexAI[c121_air_economics=1,c121_catalog_incremental=1]"
LINE = re.compile(r"\[script:\d+\]\s*\[(\d+)\].*?C121_INVEST\s+(.*)$")


def instrument(target: Path) -> None:
    """Inject the passive trace in a disposable OpexAI copy only."""
    shutil.copy2(ROOT / "tests/mechanisms/c121_investment_probe.nut",
                 target / "c121_investment_probe.nut")

    main = target / "main.nut"
    text = main.read_text(encoding="utf-8")
    text = replace_once(text, "function OpexAI::Start()",
                        'require("c121_investment_probe.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();\n",
                        "  OpexLoadSettings();\n  C121InvestSource();\n")
    main.write_text(text, encoding="utf-8")

    projects = target / "task_projects.nut"
    text = projects.read_text(encoding="utf-8")
    call = ("      local attempt = this._tryBuildAirProject(year, project, i, liveBuiltCount, passDiscards,\n"
            "                                                anchor, yy);")
    repl = (call + "\n"
            "      if (attempt.outcome == \"built\") C121InvestProject(project, i, \"built\", \"built\",\n"
            "          this._nextLineId - 1);")
    text = replace_once(text, call, repl)
    projects.write_text(text, encoding="utf-8")

    air = target / "task_air.nut"
    text = air.read_text(encoding="utf-8")
    text = replace_once(text,
        "function OpexAirFleetRefusal(line, year, code)\n{",
        "function OpexAirFleetRefusal(line, year, code)\n{\n"
        "  C121InvestFleetSnapshot(line, year, \"refuse\", code);")
    text = replace_once(text,
        "    if (addedThisPass > 0) {\n      line.lastAirFleetYear <- year;",
        "    if (addedThisPass > 0) {\n"
        "      C121InvestFleetSnapshot(line, year, \"grow\", \"ok\", have - addedThisPass, have, addedThisPass);\n"
        "      line.lastAirFleetYear <- year;")
    air.write_text(text, encoding="utf-8")

    report = target / "task_report.nut"
    text = report.read_text(encoding="utf-8")
    text = replace_once(text,
        "    local currentRevenue = profit + runCost;",
        "    local currentRevenue = profit + runCost;\n"
        "    C121InvestAnnual(line, year, vehCount, profit, currentRevenue, stationA, stationB, ratingA, ratingB);")
    report.write_text(text, encoding="utf-8")


def maybe_int(value):
    if value in (None, "na", "unknown", ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_trace(text: str):
    events, foreign = [], 0
    for line_no, raw in enumerate(text.splitlines(), 1):
        match = LINE.search(raw)
        if not match:
            continue
        owner = int(match[1])
        if owner != 0:
            foreign += 1
            continue
        fields = parse_fields(match[2])
        events.append({"line_no": line_no, "fields": fields})
    issues = []
    seqs = [maybe_int(e["fields"].get("seq")) for e in events]
    if events and (any(s is None for s in seqs) or seqs != list(range(1, len(seqs) + 1))):
        issues.append("sequence_gap_or_duplicate")
    source = [e["fields"] for e in events if e["fields"].get("event") == "source"]
    if not source:
        issues.append("missing_source_marker")
    elif any((s.get("econ"), s.get("catalog"), s.get("initial")) != ("1", "1", "0") for s in source):
        issues.append("wrong_effective_settings")

    builds = []
    for event in events:
        f = event["fields"]
        if f.get("event") == "project" and f.get("phase") == "built" and f.get("outcome") == "built":
            builds.append({k: maybe_int(f.get(k)) for k in
                           ("line", "rank", "initial_n", "target_n", "decision_n",
                            "initial_profit", "target_profit", "decision_profit",
                            "finance_now", "finance_score", "available", "fund_score")}
                          | {"key": f.get("key"), "arm": f.get("arm")})

    by_line = defaultdict(lambda: {"fleet": [], "annual": []})
    for event in events:
        f = event["fields"]
        line_id = maybe_int(f.get("line"))
        if line_id is None:
            continue
        if f.get("event") == "fleet":
            row = {k: maybe_int(f.get(k)) for k in
                   ("year", "age", "have", "target", "after", "added", "last_profit",
                    "cash", "reserve", "plane_price", "need", "wait_a", "wait_b")}
            row.update({"phase": f.get("phase"), "reason": f.get("reason")})
            by_line[line_id]["fleet"].append(row)
        elif f.get("event") == "annual":
            row = {k: maybe_int(f.get(k)) for k in
                   ("report_year", "profit_year", "age", "full_year", "vehs", "profit", "revenue",
                    "wait_a", "wait_b", "rating_a", "rating_b")}
            by_line[line_id]["annual"].append(row)

    reasons = Counter()
    growth = 0
    full_year = 0
    for state in by_line.values():
        for row in state["fleet"]:
            if row["phase"] == "refuse":
                reasons[row["reason"]] += 1
            elif row["phase"] == "grow":
                growth += row["added"] or 0
        full_year += sum((row["full_year"] or 0) == 1 for row in state["annual"])

    return {
        "events": len(events), "foreign_events": foreign, "issues": issues,
        "source_markers": source, "builds": builds, "lines": dict(by_line),
        "refusal_reasons": dict(reasons), "growth_added": growth,
        "full_year_observations": full_year,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "attribution"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    import openttdlab
    import diag_cadence_duel as duel

    folder = new_directory(args.out, ROOT / "results/c121_investment")
    before = duel.source_hashes(ROOT)
    fixture = ROOT / "tests/mechanisms/c121_investment_probe.nut"
    fixture_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    seeds = [42] if args.stage == "smoke" else [42, 100, 999, 1234, 5678]
    years = 1 if args.stage == "smoke" else 3
    names = ["c121", "c121_trace"]
    copies, arms = {}, {}
    for name in names:
        target = folder / "copies" / name / "OpexAI"
        shutil.copytree(ROOT / "ai/OpexAI", target)
        if name.endswith("_trace"):
            instrument(target)
        copies[name] = target
        arms[name] = openttdlab.local_folder(str(target), "OpexAI", SETTINGS)
    opponent = folder / "copies/AAAHogEx-115"
    shutil.copytree(ROOT / "ai/AAAHogEx-115", opponent)
    aaa = openttdlab.local_folder(str(opponent), "AAAHogEx")
    frozen = tree_hashes(folder / "copies")
    cfg = duel.bench_v2.make_cfg(1970)
    resolved = duel.bench_v2.resolve_opex_arm_settings(SPEC)
    write_new(folder / "plan.json", {
        "stage": args.stage, "years": years, "seeds": seeds, "arms": names,
        "resolved": resolved, "effective_expected": {"econ": 1, "catalog": 1, "initial": 0},
        "source_hashes": before, "source_loading": "separate_run_experiments_per_arm",
        "executed_copy_hashes": frozen, "configuration": cfg, "git_sha": None,
        "fixture_sha256": fixture_hash, "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
        "script_debug": 4, "workers": 3, "economic_verdict": "not_evaluated",
    })
    days = (date(1970 + years, 1, 1) - date(1970, 1, 1)).days + 32
    experiments = [{"arm": name, "seed": seed, "years": years, "days": days,
                    "openttd_config": cfg, "ais": (arms[name], aaa),
                    "log_path": str(folder / f"{name}_{seed}.log"),
                    "checkpoint_path": str(folder / f"{name}_{seed}.jsonl")}
                   for seed in seeds for name in names]

    duel.bench_v2.enable_savegame_cleanup()
    duel.enable_script_debug()
    duel.enable_engine_failure_capture()
    rows = list(run_isolated_arms(openttdlab.run_experiments,
        openttd_version=duel.bench_v2.OPENTTD_VERSION, opengfx_version=duel.bench_v2.OPENGFX_VERSION,
        experiments=experiments, max_workers=3, result_processor=duel.collect,
        ai_libraries=(openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"))))
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["arm"], row["seed"]].append(row)
    games = [duel.finish_game(series, years) for series in grouped.values()]
    traces = {f'{g["arm"]}_{g["seed"]}': parse_trace(Path(g["log_path"]).read_text(encoding="utf-8"))
              for g in games if g["arm"] == "c121_trace"}
    negative_events = {f'{g["arm"]}_{g["seed"]}': parse_trace(
        Path(g["log_path"]).read_text(encoding="utf-8"))["events"]
        for g in games if g["arm"] == "c121"}
    pair = [{**g, "arm": "reference" if g["arm"] == "c121" else "trace"} for g in games]
    perturbation = duel.compare(pair, ["reference", "trace"], seeds, years)
    checks = {
        "all_games": len(games) == len(experiments) and all(g["valid"] for g in games),
        "negative_control": all(v == 0 for v in negative_events.values()),
        "trace_identity": len(traces) == len(seeds) and all(
            t["events"] > 0 and t["foreign_events"] == 0 and not t["issues"] for t in traces.values()),
        "attribution_exposed": all(t["builds"] for t in traces.values()),
        "sources_unchanged": before == duel.source_hashes(ROOT),
        "copies_unchanged": frozen == tree_hashes(folder / "copies"),
        "fixture_unchanged": fixture_hash == hashlib.sha256(fixture.read_bytes()).hexdigest(),
    }
    write_new(folder / "report.json", {"checks": checks, "pass": all(checks.values()),
              "games": games, "traces": traces, "negative_events": negative_events,
              "perturbation": perturbation, "economic_verdict": "not_evaluated"})
    print(json.dumps(checks, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
