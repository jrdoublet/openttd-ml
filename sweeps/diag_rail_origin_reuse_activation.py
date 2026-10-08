"""Minimal first-activation diagnostic for rail origin-reuse fallback.

Production sources are never edited. Two disposable OpexAI copies receive the
same one-shot probe. The only policy difference is ``rail_origin_reuse`` (0/1);
fallback=1, pax=1 and freight=0 are fixed in both arms, so the subsettings are
inert in the reference.

The probe logs exactly once, at the first fresh<TOP_K generation with at least
one already-served rail endpoint. For deferred admission (the normal mixed
rail-generation path), both arms log from ``OpexRailOriginReuseFinalize`` after
the variant has paid its reuse evaluation. This records whether the first
activation produced any semantic reuse candidates and how many measured
generation opcodes the evaluation added. It is diagnostic evidence only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re
import shutil
import sys


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab  # noqa: E402
import diag_cadence_duel as duel  # noqa: E402
from diag_c121_postbuild import run_isolated_arms  # noqa: E402
from diag_r1_r3_mechanisms import new_directory, write_new  # noqa: E402
from run_mechanism_fixtures import replace_once, tree_hashes  # noqa: E402


PROBE = re.compile(r"R100TER_ACTIVATION\s+(.*)$")


def parse_fields(text: str) -> dict[str, int | str]:
    out: dict[str, int | str] = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            out[key] = int(value)
        except ValueError:
            out[key] = value
    return out


def instrument(target: Path) -> None:
    globals_path = target / "globals_pre.nut"
    globals_text = globals_path.read_text(encoding="utf-8")
    globals_text = replace_once(
        globals_text,
        "STAGED_BOOTSTRAP <- true;\n",
        "STAGED_BOOTSTRAP <- true;\nR100TER_REUSE_PROBE_LOGGED <- false; /* staged diagnostic only */\n",
    )
    globals_path.write_text(globals_text, encoding="utf-8")

    path = target / "candidates.nut"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "  local needFallbackReuse = all.len() < TOP_K && stats.pairsOriginServed > 0;\n",
        "  local r100terFreshBefore = all.len();\n"
        "  local needFallbackReuse = all.len() < TOP_K && stats.pairsOriginServed > 0;\n",
    )
    result_anchor = (
        "  local result = { all = all.len(), candidates = all, best = best,\n"
        "                   bands = OpexBands(all), stats = stats,\n"
        "                   opcodes = opsPax + opsFreight + opsReuse + opsRank, profile = profile };\n"
    )
    result_replacement = result_anchor + (
        "  if (needFallbackReuse) {\n"
        "    result.r100terNeedFallback <- true;\n"
        "    result.r100terFreshBefore <- r100terFreshBefore;\n"
        "    result.r100terPairsOriginServed <- stats.pairsOriginServed;\n"
        "    result.r100terBaseOpcodes <- result.opcodes;\n"
        "    result.r100terRunFallback <- runFallbackReuse;\n"
        "    result.r100terProbeAtFinalize <- deferReuseAdmission;\n"
        "    result.r100terGeneratePax <- generatePax;\n"
        "    result.r100terGenerateFreight <- generateFreight;\n"
        "    result.r100terTargeted <- targetKind != null && targetId >= 0;\n"
        "    if (!deferReuseAdmission && !R100TER_REUSE_PROBE_LOGGED) {\n"
        "      ::R100TER_REUSE_PROBE_LOGGED = true;\n"
        "      local d = AIDate.GetCurrentDate();\n"
        "      AILog.Info(\"R100TER_ACTIVATION date=\" + AIDate.GetYear(d) + \"-\"\n"
        "          + AIDate.GetMonth(d) + \"-\" + AIDate.GetDayOfMonth(d)\n"
        "          + \" fresh=\" + r100terFreshBefore + \" pairs_origin=\" + stats.pairsOriginServed\n"
        "          + \" run=\" + (runFallbackReuse ? 1 : 0) + \" deferred=0\"\n"
        "          + \" pax=\" + (generatePax ? 1 : 0) + \" freight=\" + (generateFreight ? 1 : 0)\n"
        "          + \" targeted=\" + ((targetKind != null && targetId >= 0) ? 1 : 0)\n"
        "          + \" base_ops=\" + result.r100terBaseOpcodes + \" total_ops=\" + result.opcodes\n"
        "          + \" extra_ops=\" + opsReuse\n"
        "          + \" reuse_total=\" + (reuseFallback != null ? reuseFallback.reuseTotal : 0)\n"
        "          + \" admitted=\" + (reuseFallback != null ? reuseFallback.reuseAdmitted : 0));\n"
        "    }\n"
        "  }\n"
    )
    text = replace_once(text, result_anchor, result_replacement)

    finalize_anchor = "  if (reuse.len() == 0) {\n"
    finalize_probe = (
        "  if ((\"r100terNeedFallback\" in set) && set.r100terNeedFallback\n"
        "      && (\"r100terProbeAtFinalize\" in set) && set.r100terProbeAtFinalize\n"
        "      && !R100TER_REUSE_PROBE_LOGGED) {\n"
        "    ::R100TER_REUSE_PROBE_LOGGED = true;\n"
        "    local d = AIDate.GetCurrentDate();\n"
        "    local baseOps = (\"r100terBaseOpcodes\" in set) ? set.r100terBaseOpcodes : set.opcodes;\n"
        "    AILog.Info(\"R100TER_ACTIVATION date=\" + AIDate.GetYear(d) + \"-\"\n"
        "        + AIDate.GetMonth(d) + \"-\" + AIDate.GetDayOfMonth(d)\n"
        "        + \" fresh=\" + set.r100terFreshBefore + \" pairs_origin=\" + set.r100terPairsOriginServed\n"
        "        + \" run=\" + (set.r100terRunFallback ? 1 : 0) + \" deferred=1\"\n"
        "        + \" pax=\" + (set.r100terGeneratePax ? 1 : 0)\n"
        "        + \" freight=\" + (set.r100terGenerateFreight ? 1 : 0)\n"
        "        + \" targeted=\" + (set.r100terTargeted ? 1 : 0)\n"
        "        + \" base_ops=\" + baseOps + \" total_ops=\" + set.opcodes\n"
        "        + \" extra_ops=\" + (set.opcodes - baseOps)\n"
        "        + \" reuse_total=\" + reuse.len()\n"
        "        + \" joinable=\" + (reuseStats != null ? reuseStats.originReuseJoinable : 0)\n"
        "        + \" fast_negative=\" + (reuseStats != null ? reuseStats.originReuseFastNegative : 0));\n"
        "  }\n"
    ) + finalize_anchor
    text = replace_once(text, finalize_anchor, finalize_probe)
    path.write_text(text, encoding="utf-8")


def activation(log_path: Path) -> dict | None:
    matches = []
    for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PROBE.search(raw)
        if match:
            matches.append(parse_fields(match.group(1)))
    if not matches:
        return None
    return {"count": len(matches), "first": matches[0]}


def checkpoints(path: Path) -> dict[str, dict]:
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        envelope = json.loads(raw)
        for record in envelope.get("records") or []:
            run = record.get("run") or []
            if run and run[0] == "OpexAI":
                out[str(envelope.get("date"))] = record
                break
    return out


def checkpoint_view(row: dict) -> dict:
    return {
        "money": row.get("money"),
        "current_loan": row.get("current_loan"),
        "company_value": row.get("company_value"),
        "n_vehicles": row.get("n_vehicles"),
        "primary_vehicles_by_mode": row.get("primary_vehicles_by_mode") or {},
        "air_primary_vehicles": row.get("air_primary_vehicles"),
        "air_passenger_capacity": row.get("air_passenger_capacity"),
        "n_stations": row.get("n_stations"),
        "stations_by_facility": row.get("stations_by_facility") or {},
    }


def first_checkpoint_difference(ref: dict[str, dict], var: dict[str, dict]) -> dict | None:
    previous_equal = None
    for current_date in sorted(set(ref) & set(var)):
        a, b = checkpoint_view(ref[current_date]), checkpoint_view(var[current_date])
        differences = {key: {"reference": a[key], "variant": b[key]}
                       for key in a if a[key] != b[key]}
        if not differences:
            previous_equal = current_date
            continue
        return {"date": current_date, "previous_equal_date": previous_equal,
                "differences": differences}
    return None


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=841478)
    parser.add_argument("--years", type=int, default=4)
    args = parser.parse_args(argv)

    folder = new_directory(args.out, ROOT / "results/rail_origin_reuse_activation")
    production = ROOT / "ai" / "OpexAI"
    before = tree_hashes(production)
    common = (
        ("decision_log", 0),
        ("rail_geometry_guard", 1),
        ("rail_origin_reuse_fallback", 1),
        ("rail_origin_reuse_pax", 1),
        ("rail_origin_reuse_freight", 0),
    )
    arms = {}
    staged = {}
    for name, enabled in (("reference", 0), ("variant", 1)):
        target = folder / "copies" / name / "OpexAI"
        shutil.copytree(production, target)
        instrument(target)
        arms[name] = openttdlab.local_folder(
            str(target), "OpexAI", common + (("rail_origin_reuse", enabled),))
        staged[name] = tree_hashes(target)

    opponent = folder / "copies" / "AAAHogEx-115"
    shutil.copytree(ROOT / "ai" / "AAAHogEx-115", opponent)
    aaa = openttdlab.local_folder(str(opponent), "AAAHogEx")
    frozen = tree_hashes(folder / "copies")
    cfg = duel.bench_v2.make_cfg(1970)
    days = (date(1970 + args.years, 1, 1) - date(1970, 1, 1)).days + 32
    write_new(folder / "plan.json", {
        "kind": "rail_origin_reuse_first_activation_diagnostic_not_adoption",
        "seed": args.seed, "years": args.years,
        "policy_difference": "rail_origin_reuse 0 vs 1 only; fallback=1 pax=1 freight=0 in both",
        "decision_log": 0,
        "probe": "same one-shot staged source instrumentation in both arms",
        "production_hashes": before,
        "staged_hashes": staged,
        "configuration": cfg,
    })

    experiments = [{
        "arm": name, "seed": args.seed, "years": args.years, "days": days,
        "openttd_config": cfg, "ais": (arms[name], aaa),
        "log_path": str(folder / f"{name}_{args.seed}.log"),
        "checkpoint_path": str(folder / f"{name}_{args.seed}.jsonl"),
    } for name in ("reference", "variant")]
    duel.bench_v2.enable_savegame_cleanup()
    duel.enable_script_debug()
    duel.enable_engine_failure_capture()
    rows = list(run_isolated_arms(
        openttdlab.run_experiments,
        openttd_version=duel.bench_v2.OPENTTD_VERSION,
        opengfx_version=duel.bench_v2.OPENGFX_VERSION,
        experiments=experiments,
        max_workers=2,
        result_processor=duel.collect,
        ai_libraries=(
            openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["arm"], row["seed"]].append(row)
    games = [duel.finish_game(series, args.years) for series in grouped.values()]
    game_by_arm = {g["arm"]: g for g in games}

    activations = {
        name: activation(folder / f"{name}_{args.seed}.log")
        for name in ("reference", "variant")
    }
    ref_event = activations["reference"]["first"] if activations["reference"] else None
    var_event = activations["variant"]["first"] if activations["variant"] else None
    same_exposure = bool(ref_event and var_event) and all(
        ref_event.get(key) == var_event.get(key)
        for key in ("date", "fresh", "pairs_origin", "deferred", "pax", "freight", "targeted", "base_ops")
    )
    variant_extra = int(var_event.get("extra_ops", 0)) if var_event else None
    first_diff = first_checkpoint_difference(
        checkpoints(folder / f"reference_{args.seed}.jsonl"),
        checkpoints(folder / f"variant_{args.seed}.jsonl"),
    )
    checks = {
        "all_games_valid": len(games) == 2 and all(g.get("valid") for g in games),
        "one_probe_per_arm": all(value is not None and value["count"] == 1
                                 for value in activations.values()),
        "same_first_exposure": same_exposure,
        "reference_did_not_run_reuse": bool(ref_event) and int(ref_event.get("run", -1)) == 0,
        "variant_ran_reuse": bool(var_event) and int(var_event.get("run", -1)) == 1,
        "variant_measured_extra_ops": variant_extra is not None and variant_extra > 0,
        "production_sources_unchanged": before == tree_hashes(production),
        "staged_copies_unchanged": frozen == tree_hashes(folder / "copies"),
    }
    report = {
        "checks": checks,
        "diagnostic_pass": all(checks.values()),
        "activations": activations,
        "first_checkpoint_divergence": first_diff,
        "games": games,
        "economic_verdict": "not_evaluated",
    }
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "activations": activations,
                      "first_checkpoint_divergence": first_diff}, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
