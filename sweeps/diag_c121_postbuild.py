"""Bounded post-build diagnostic using the existing duel harness on copied AIs.

No production writes, no game on import, no economic adoption verdict.
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
from parallel_latency_audit import distribution, difference
from harness import parse_fields
from run_mechanism_fixtures import replace_once, tree_hashes
from diag_r1_r3_mechanisms import new_directory, write_new

BASE_SETTINGS = {"c115": (), "c121": (("c121_air_economics", 1), ("c121_catalog_incremental", 1))}
SPECS = {"c115": "OpexAI", "c121": "OpexAI[c121_air_economics=1,c121_catalog_incremental=1]"}
LINE = re.compile(r"\[script:\d+\]\s*\[(\d+)\].*?POSTBUILD\s+(.*)$")


def instrument(target):
    shutil.copy2(ROOT / "tests/mechanisms/c121_postbuild_probe.nut", target / "c121_postbuild_probe.nut")
    main = target / "main.nut"
    main.write_text(replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
                                'require("c121_postbuild_probe.nut");\n\nfunction OpexAI::Start()'), encoding="utf-8")
    path = target / "scheduler_tasks.nut"
    path.write_text(replace_once(path.read_text(encoding="utf-8"),
                                "function OpexAI::_dispatchProjects(task, year)\n{",
                                "function OpexAI::_dispatchProjects(task, year)\n{\n  PBDispatch(this);"), encoding="utf-8")
    path = target / "task_projects.nut"
    text = path.read_text(encoding="utf-8")
    start = text.index("function OpexAI::_tryBuildProjects(year)")
    end = text.index("function OpexAI::_rebuildProjects(", start)
    block = text[start:end]
    edits = [
        ("function OpexAI::_tryBuildProjects(year)\n{", "function OpexAI::_tryBuildProjects(year)\n{\n  PBBegin(this);"),
        ("if (c83TargetedRegens > 0) return true;", 'if (c83TargetedRegens > 0) { PBEnd("watcher_regen"); return true; }'),
        ('      if (c121FirstYearAirBatch) c121DeadSkipped++;', '      PB_STATE.dead++;\n      if (c121FirstYearAirBatch) c121DeadSkipped++;'),
        ('          c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";',
         '          c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";\n'
         '          PBLog("stop", "reason=" + c75StopReason + " mode=" + project.mode + " rank=" + i\n'
         '              + " finance=" + projCap + " available=" + availCap + " threshold=" + c75KPass);\n'
         '          if (c75StopReason == "k_pass") PBKPassStop(this, project, i, projCap, c75KPass, availCap);'),
        ('    local mode = project.mode;', '    PBLog("attempt", " mode=" + project.mode + " rank=" + i);\n    local mode = project.mode;'),
        ('    if (railBuilt) builtCount++;', '    if (railBuilt) { PBOutcome({ mode = "rail" }, -1, "built"); builtCount++; }'),
        ('        return true;', '        PBEnd("rail_pending");\n        return true;'),
        ('  if (builtCount > 0 || hadAbandons) {',
         '  if (builtCount > 0 || hadAbandons) {\n'
         '    local pbFleet = PBPhaseBegin("fleet");'),
        ('    if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {',
         '    PBPhaseEnd(pbFleet);\n'
         '    local pbKind = (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) ? "staged_full"\n'
         '        : ((PORTFOLIO_CACHE && this._projects != null && ("candidateGroups" in this._projects)) ? "incremental" : "full");\n'
         '    local pbRegen = PBPhaseBegin(pbKind);\n'
         '    if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {'),
        ('    if (pcost != null) pcost.regenOps = OpexOpsMeasureEnd(pcost.mark);',
         '    PBPhaseEnd(pbRegen);\n    if (pcost != null) pcost.regenOps = OpexOpsMeasureEnd(pcost.mark);'),
        ('    return true;\n  }\n  if (pcost != null)', '    PBEnd(c75StopReason);\n    return true;\n  }\n  if (pcost != null)'),
        ('  return false;\n}', '  PBEnd(c75StopReason);\n  return false;\n}'),
    ]
    for old, new in edits:
        block = replace_once(block, old, new)
    anchor = "      passDiscards = attempt.discards;"
    if block.count(anchor) != 5:
        raise ValueError("Expected five executor outcome sites")
    block = block.replace(anchor, "      PBOutcome(project, i, attempt.outcome);\n" + anchor)
    # Whitespace is part of the log contract (fields must remain tokenized).
    block = block.replace('PBLog("stop", "reason="', 'PBLog("stop", " reason="')
    path.write_text(text[:start] + block + text[end:], encoding="utf-8")


def number(fields, name):
    try:
        value = int(fields[name])
        return value if value >= 0 else None
    except (KeyError, ValueError, TypeError):
        return None


def audit(text):
    """One game/log. Explicit owner/session/sequence; no pairing across reloads.

    Closed phase costs are disjoint fleet/regeneration, not additive with the
    enclosing pass or inter-investment gaps. Unknown money stays unknown.
    """
    groups = defaultdict(list)
    sessions = defaultdict(int)
    issues, windows, gaps, stops, kpass_stops, kpass_tails = [], [], [], [], [], []
    for line_no, raw in enumerate(text.splitlines(), 1):
        if "LOAD_RECONCILE" in raw:
            match = re.search(r"\[script:\d+\]\s*\[(\d+)\]", raw)
            if match:
                sessions[int(match[1])] += 1
        match = LINE.search(raw)
        if not match:
            continue
        owner = int(match[1])
        f = parse_fields(match[2])
        event = {"line": line_no, "company": owner, "session": sessions[owner], "fields": f}
        if f.get("v") != "1" or any(number(f, k) is None for k in ("seq", "pass", "day", "tick")):
            issues.append({"reason": "invalid_event", **event})
            continue
        groups[owner, sessions[owner]].append(event)
    counts = Counter()
    for (owner, session), events in groups.items():
        # Contradictory sequences invalidate a stream rather than selecting a
        # convenient duplicate or inferring an undocumented restart.
        seqs = [number(e["fields"], "seq") for e in events]
        if seqs[0] != 1 or seqs != sorted(set(seqs)) or any(b != a + 1 for a, b in zip(seqs, seqs[1:])):
            issues.append({"reason": "sequence_collision_or_gap", "company": owner, "session": session})
            continue
        pending, passes, waiting = {}, {}, {}
        previous_build = {}
        last_built_by_pass = {}
        for e in events:
            f = e["fields"]
            edge, pid = f.get("edge"), number(f, "pass")
            counts[edge] += 1
            if edge == "pass_begin":
                passes[pid] = e
            elif edge == "pass_end":
                if passes.pop(pid, None) is None:
                    issues.append({"reason": "unmatched_pass_end", **e})
            elif edge == "phase_begin":
                key = pid, f.get("kind")
                if key in pending:
                    issues.append({"reason": "duplicate_phase_begin", **e})
                    pending[key] = None
                else:
                    pending[key] = e
            elif edge == "phase_end":
                key = pid, f.get("kind")
                begin = pending.pop(key, None)
                days = difference(number(f, "start_day"), number(f, "end_day"))
                ticks = difference(number(f, "start_tick"), number(f, "end_tick"))
                if begin is None or days is None or ticks is None or number(f, "ops") is None:
                    issues.append({"reason": "invalid_phase", **e})
                    continue
                bf = begin["fields"]
                if not (number(bf, "day") <= number(f, "start_day") <= number(f, "end_day") <= number(f, "day")
                        and number(bf, "tick") <= number(f, "start_tick") <= number(f, "end_tick") <= number(f, "tick")):
                    issues.append({"reason": "phase_boundary_order", **e})
                    continue
                windows.append({"company": owner, "session": session, "pass": pid, "kind": key[1],
                                "day": number(f, "start_day"), "days": days, "ticks": ticks,
                                "ops": number(f, "ops"), "begin_line": begin["line"], "end_line": e["line"]})
                if key[1] != "fleet":
                    if pid in last_built_by_pass:
                        build = last_built_by_pass[pid]
                        gaps.append({"company": owner, "session": session, "pass": pid,
                                     "metric": "last_build_to_regen_end", "begin_line": build["line"], "end_line": e["line"],
                                     "days": difference(number(build["fields"], "day"), number(f, "end_day")),
                                     "ticks": difference(number(build["fields"], "tick"), number(f, "end_tick"))})
                    waiting[pid] = {"end": e, "remaining": {"dispatch", "attempt", "built"}}
            if edge == "stop":
                stops.append({**e, "financeable_at_stop":
                    number(f, "finance") <= number(f, "available")
                    if number(f, "finance") is not None and number(f, "available") is not None else None})
            elif edge == "kpass_stop":
                kpass_stops.append({**e, "financeable_at_stop":
                    number(f, "finance") <= number(f, "available")
                    if number(f, "finance") is not None and number(f, "available") is not None else None})
            elif edge == "kpass_tail":
                kpass_tails.append({**e,
                    "affordable": number(f, "affordable") == 1 if number(f, "affordable") is not None else None,
                    "below_kpass": number(f, "below_kpass") == 1 if number(f, "below_kpass") is not None else None})
            built = edge == "outcome" and f.get("outcome") == "built"
            metric = "built" if built else edge
            if metric in {"dispatch", "attempt", "built"}:
                for waiting_pass, state in list(waiting.items()):
                    if metric not in state["remaining"]:
                        continue
                    start = state["end"]
                    gaps.append({"company": owner, "session": session, "pass": waiting_pass,
                                 "metric": "regen_to_" + metric, "begin_line": start["line"], "end_line": e["line"],
                                 "days": difference(number(start["fields"], "day"), number(f, "day")),
                                 "ticks": difference(number(start["fields"], "tick"), number(f, "tick")),
                                 "mode": f.get("mode")})
                    state["remaining"].remove(metric)
                    if not state["remaining"]:
                        del waiting[waiting_pass]
            if built:
                last_built_by_pass[pid] = e
                family = "fleet" if f.get("mode") == "fleet" else "new_line"
                for label in ("any", family):
                    if label in previous_build:
                        start = previous_build[label]
                        gaps.append({"company": owner, "session": session, "metric": "build_gap_" + label,
                                     "begin_line": start["line"], "end_line": e["line"],
                                     "days": difference(number(start["fields"], "day"), number(f, "day")),
                                     "ticks": difference(number(start["fields"], "tick"), number(f, "tick"))})
                    previous_build[label] = e
        for key in pending:
            issues.append({"reason": "censored_phase", "company": owner, "session": session, "key": key})
        for pid in passes:
            issues.append({"reason": "censored_pass", "company": owner, "session": session, "pass": pid})
        for pid, state in waiting.items():
            issues.append({"reason": "censored_next_event", "company": owner, "session": session,
                           "pass": pid, "remaining": sorted(state["remaining"])})
    def summaries(records, key):
        return {label: {unit: distribution(r.get(unit) for r in records if r[key] == label)
                        for unit in ("days", "ticks", "ops")}
                for label in sorted({r[key] for r in records})}
    return {"counts": dict(counts), "windows": windows, "gaps": gaps, "stops": stops,
            "kpass_stops": kpass_stops, "kpass_tails": kpass_tails,
            "issues": issues, "phase_summary": summaries(windows, "kind"),
            "gap_summary": summaries(gaps, "metric"),
            "continuous_affordable_wait": None,
            "scope": "observed_instrumented_trajectory_not_causal_savings"}


def run_isolated_arms(run_experiments, experiments, **kwargs):
    """One loader invocation per arm: same AI name cannot select two sources."""
    for arm in dict.fromkeys(exp["arm"] for exp in experiments):
        batch = [exp for exp in experiments if exp["arm"] == arm]
        yield from run_experiments(experiments=batch, **kwargs)


def probe_identity(logs):
    """Observe the probe in every arm, including negative controls. Fail closed."""
    observations = {}
    for key, text in logs.items():
        arm, seed = key
        events = [m for line in text.splitlines() if (m := LINE.search(line))]
        opex = sum(int(m[1]) == 0 for m in events)
        foreign = len(events) - opex
        expected = arm.endswith("_trace")
        observations[f"{arm}_{seed}"] = {
            "expected_probe": expected, "opex_events": opex, "foreign_events": foreign,
            "matches": (opex > 0 if expected else opex == 0) and foreign == 0,
        }
    return {"pass": bool(observations) and all(v["matches"] for v in observations.values()),
            "observations": observations}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "exposure"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    import openttdlab
    import diag_cadence_duel as duel
    folder = new_directory(args.out, ROOT / "results/c121_postbuild_latency")
    before = duel.source_hashes(ROOT)
    fixture = ROOT / "tests/mechanisms/c121_postbuild_probe.nut"
    fixture_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    seeds = [42] if args.stage == "smoke" else [42, 100, 999, 1234, 5678]
    years = 1 if args.stage == "smoke" else 3
    # Le smoke doit prouver la source chargee, pas seulement la presence de la
    # sonde : chaque modele a donc un controle negatif et un controle positif.
    names = ["c115", "c115_trace", "c121", "c121_trace"]
    copies, arms, resolved = {}, {}, {}
    for name in names:
        target = folder / "copies" / name / "OpexAI"
        shutil.copytree(ROOT / "ai/OpexAI", target)
        if name.endswith("_trace"):
            instrument(target)
        copies[name] = target
        model = name.split("_")[0]
        arms[name] = openttdlab.local_folder(str(target), "OpexAI", BASE_SETTINGS[model])
        resolved[name] = duel.bench_v2.resolve_opex_arm_settings(SPECS[model])
    opponent = folder / "copies/AAAHogEx-115"
    shutil.copytree(ROOT / "ai/AAAHogEx-115", opponent)
    aaa = openttdlab.local_folder(str(opponent), "AAAHogEx")
    frozen = tree_hashes(folder / "copies")
    cfg = duel.bench_v2.make_cfg(1970)
    write_new(folder / "plan.json", {"stage": args.stage, "years": years, "seeds": seeds,
              "arms": names, "resolved": resolved, "source_hashes": before,
              "source_loading": "separate_run_experiments_per_arm",
              "executed_copy_hashes": frozen, "configuration": cfg, "git_sha": None,
              "fixture_sha256": fixture_hash, "image": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
              "script_debug": 4, "workers": 3, "economic_verdict": "not_evaluated"})
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
    identity = probe_identity({(g["arm"], g["seed"]): Path(g["log_path"]).read_text(encoding="utf-8")
                               for g in games})
    audits = {f'{g["arm"]}_{g["seed"]}': audit(Path(g["log_path"]).read_text(encoding="utf-8"))
              for g in games if g["arm"].endswith("_trace")}
    checks = {
        "probe_identity": identity["pass"],
        "all_games": len(games) == len(experiments) and all(g["valid"] for g in games),
        "sources_unchanged": before == duel.source_hashes(ROOT),
        "copies_unchanged": frozen == tree_hashes(folder / "copies"),
        "fixture_unchanged": fixture_hash == hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "exposure": len(audits) == 2 * len(seeds) and all(
            a["counts"].get("outcome", 0) > 0 and any(w["kind"] != "fleet" for w in a["windows"])
            for a in audits.values()),
        "trace_integrity": all(all(i["reason"].startswith("censored_") for i in a["issues"])
                               for a in audits.values()),
    }
    perturbation = {}
    if args.stage == "exposure" and all(checks.values()):
        for model in BASE_SETTINGS:
            pair = [{**g, "arm": "reference" if g["arm"] == model else "trace"}
                    for g in games if g["arm"] in (model, model + "_trace")]
            perturbation[model] = duel.compare(pair, ["reference", "trace"], seeds, years)
    write_new(folder / "report.json", {"checks": checks, "pass": all(checks.values()),
              "probe_identity": identity,
              "games": games, "audits": audits, "perturbation": perturbation,
              "economic_verdict": "not_evaluated"})
    print(json.dumps(checks, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
