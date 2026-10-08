"""Isolate the startup-setting opcode cost of ``rail_origin_reuse``.

Four copied-source arms are run for one seed:

* control_a/control_b: identical production setting-load path, reuse=0;
* equated_reference/equated_variant: both unconditionally read/assign the six
  child reuse settings and reorder two semantically-inert parent checks so a
  fresh candidate never pays a parent-dependent short-circuit; reuse is 0/1.

All four copies also carry the same one-shot first-fallback probe from
``diag_rail_origin_reuse_activation``.  Production is never edited.  The
experiment separates ordinary same-code repeat noise, the cost of the six
startup GetSetting calls, and the actual reuse policy after those reads have
been cost-equalized.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import shutil
import sys


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import openttdlab  # noqa: E402
import diag_cadence_duel as duel  # noqa: E402
from diag_c121_postbuild import run_isolated_arms  # noqa: E402
from diag_r1_r3_mechanisms import new_directory, write_new  # noqa: E402
from diag_rail_origin_reuse_activation import (  # noqa: E402
    activation,
    checkpoints,
    first_checkpoint_difference,
    instrument,
)
from run_mechanism_fixtures import replace_once, tree_hashes  # noqa: E402


SETTINGS_OLD = """  RAIL_ORIGIN_REUSE_MULTILINE_MATCH = RAIL_ORIGIN_REUSE
      && AIController.GetSetting(\"rail_origin_reuse_multiline_match\") != 0;
  RAIL_ORIGIN_REUSE_CROSS_CARGO = RAIL_ORIGIN_REUSE
      && AIController.GetSetting(\"rail_origin_reuse_cross_cargo\") != 0;
  RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW = RAIL_ORIGIN_REUSE
      && AIController.GetSetting(\"rail_origin_reuse_air_priority_shadow\") != 0;
  RAIL_ORIGIN_REUSE_AIR_PRIORITY = RAIL_ORIGIN_REUSE
      && AIController.GetSetting(\"rail_origin_reuse_air_priority\") != 0;
  RAIL_ORIGIN_REUSE_SEARCH_CAP = RAIL_ORIGIN_REUSE
      ? AIController.GetSetting(\"rail_origin_reuse_search_cap_k\") * 1000 : 0;
  RAIL_ORIGIN_REUSE_SEARCH_SUPERSEDE = RAIL_ORIGIN_REUSE
      && AIController.GetSetting(\"rail_origin_reuse_search_supersede\") != 0;
"""

SETTINGS_EQUALIZED = """  /* R100ter copied-source diagnostic: identical child-setting reads AND assignments.
   * All six child settings are fixed to 0 in this protocol, so removing the parent mask changes no
   * child semantics while eliminating the short-circuit/ternary opcode difference between arms. */
  RAIL_ORIGIN_REUSE_MULTILINE_MATCH = AIController.GetSetting(\"rail_origin_reuse_multiline_match\") != 0;
  RAIL_ORIGIN_REUSE_CROSS_CARGO = AIController.GetSetting(\"rail_origin_reuse_cross_cargo\") != 0;
  RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW = AIController.GetSetting(\"rail_origin_reuse_air_priority_shadow\") != 0;
  RAIL_ORIGIN_REUSE_AIR_PRIORITY = AIController.GetSetting(\"rail_origin_reuse_air_priority\") != 0;
  RAIL_ORIGIN_REUSE_SEARCH_CAP = AIController.GetSetting(\"rail_origin_reuse_search_cap_k\") * 1000;
  RAIL_ORIGIN_REUSE_SEARCH_SUPERSEDE = AIController.GetSetting(\"rail_origin_reuse_search_supersede\") != 0;
"""


def equalize_setting_reads(target: Path) -> None:
    path = target / "settings.nut"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, SETTINGS_OLD, SETTINGS_EQUALIZED)
    path.write_text(text, encoding="utf-8")


def equalize_inert_parent_checks(target: Path) -> None:
    """Keep semantics, but avoid reading the parent on paths where reuse cannot run."""
    path = target / "candidates.nut"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "  local runEqualPriorityReuse = stats.pairsOriginServed > 0 && RAIL_ORIGIN_REUSE\n"
        "      && !RAIL_ORIGIN_REUSE_FALLBACK;\n",
        "  local runEqualPriorityReuse = stats.pairsOriginServed > 0 && !RAIL_ORIGIN_REUSE_FALLBACK\n"
        "      && RAIL_ORIGIN_REUSE;\n",
    )
    path.write_text(text, encoding="utf-8")

    path = target / "builder_rail.nut"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "    local strictOriginReuseJoin = RAIL_ORIGIN_REUSE\n"
        "        && (\"originServed\" in candidate) && candidate.originServed\n"
        "        && (\"joinEnd\" in candidate);\n",
        "    local strictOriginReuseJoin = (\"originServed\" in candidate) && candidate.originServed\n"
        "        && RAIL_ORIGIN_REUSE && (\"joinEnd\" in candidate);\n",
    )
    path.write_text(text, encoding="utf-8")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=841478)
    parser.add_argument("--years", type=int, default=4)
    args = parser.parse_args(argv)

    folder = new_directory(args.out, ROOT / "results/rail_origin_reuse_startup_cost")
    production = ROOT / "ai" / "OpexAI"
    before = tree_hashes(production)
    common = (
        ("decision_log", 0),
        ("rail_geometry_guard", 1),
        ("rail_origin_reuse_fallback", 1),
        ("rail_origin_reuse_pax", 1),
        ("rail_origin_reuse_freight", 0),
    )
    specs = (
        ("control_a", 0, False),
        ("control_b", 0, False),
        ("equated_reference", 0, True),
        ("equated_variant", 1, True),
    )
    arms = {}
    staged = {}
    for name, enabled, equalized in specs:
        target = folder / "copies" / name / "OpexAI"
        shutil.copytree(production, target)
        instrument(target)
        if equalized:
            equalize_setting_reads(target)
            equalize_inert_parent_checks(target)
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
        "kind": "rail_origin_reuse_startup_cost_isolation_not_adoption",
        "seed": args.seed, "years": args.years,
        "arms": [name for name, _, _ in specs],
        "equalized_reads": [
            "rail_origin_reuse_multiline_match", "rail_origin_reuse_cross_cargo",
            "rail_origin_reuse_air_priority_shadow", "rail_origin_reuse_air_priority",
            "rail_origin_reuse_search_cap_k", "rail_origin_reuse_search_supersede",
        ],
        "equalized_inert_parent_checks": [
            "runEqualPriorityReuse checks fallback before parent",
            "strictOriginReuseJoin checks originServed before parent",
        ],
        "production_hashes": before, "staged_hashes": staged,
        "decision_log": 0, "configuration": cfg,
    })

    experiments = [{
        "arm": name, "seed": args.seed, "years": args.years, "days": days,
        "openttd_config": cfg, "ais": (arms[name], aaa),
        "log_path": str(folder / f"{name}_{args.seed}.log"),
        "checkpoint_path": str(folder / f"{name}_{args.seed}.jsonl"),
    } for name, _, _ in specs]
    duel.bench_v2.enable_savegame_cleanup()
    duel.enable_script_debug()
    duel.enable_engine_failure_capture()
    rows = list(run_isolated_arms(
        openttdlab.run_experiments,
        openttd_version=duel.bench_v2.OPENTTD_VERSION,
        opengfx_version=duel.bench_v2.OPENGFX_VERSION,
        experiments=experiments,
        max_workers=4,
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

    acts = {name: activation(folder / f"{name}_{args.seed}.log") for name, _, _ in specs}
    cks = {name: checkpoints(folder / f"{name}_{args.seed}.jsonl") for name, _, _ in specs}
    comparisons = {
        "same_code_repeat": first_checkpoint_difference(cks["control_a"], cks["control_b"]),
        "startup_reads_only": first_checkpoint_difference(cks["control_a"], cks["equated_reference"]),
        "equalized_policy": first_checkpoint_difference(cks["equated_reference"], cks["equated_variant"]),
    }
    checks = {
        "all_games_valid": len(games) == 4 and all(g.get("valid") for g in games),
        "production_sources_unchanged": before == tree_hashes(production),
        "staged_copies_unchanged": frozen == tree_hashes(folder / "copies"),
    }
    report = {
        "checks": checks,
        "activations": acts,
        "first_checkpoint_divergences": comparisons,
        "games": games,
        "economic_verdict": "not_evaluated",
    }
    write_new(folder / "report.json", report)
    print(json.dumps({"checks": checks, "activations": acts,
                      "first_checkpoint_divergences": comparisons}, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
