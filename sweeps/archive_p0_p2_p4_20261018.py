#!/usr/bin/env python3
"""Freeze selected October 2026 P0/P2/P4 research evidence, without simulation.

Run from the repository root. This tool only creates files inside
evidence/review/p0_p2_p4_20261018; it never changes source worktrees.
Use verify_p0_p2_p4_archive_20261018.py to check every archived byte.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "evidence/review/p0_p2_p4_20261018"
STAMP = (2026, 10, 18, 0, 0, 0)
EXTENSIONS = (".json", ".jsonl", ".manifest.json")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)
    return done.stdout.decode("utf-8", errors="replace").strip()


def stage(name: str) -> str:
    return f"results/{name}"


def exact(group: dict, *paths: str) -> None:
    for path in paths:
        if not (ROOT / path).is_file():
            raise FileNotFoundError(f"Required archival evidence missing: {path}")
        group[path] = (ROOT / path).read_bytes()


def matching(group: dict, directory: str, patterns: tuple[str, ...]) -> None:
    folder = ROOT / directory
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    for pattern in patterns:
        for path in sorted(folder.glob(pattern)):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                group[rel] = path.read_bytes()


def campaign(group: dict, worktree: str, *names: str) -> None:
    for name in names:
        for suffix in EXTENSIONS:
            exact(group, f"{stage(worktree)}/results/{name}{suffix}")


def extra_result(group: dict, worktree: str, *names: str) -> None:
    exact(group, *(f"{stage(worktree)}/results/{x}" for x in names))


def scripts(group: dict, worktree: str, *patterns: str) -> None:
    matching(group, f"{stage(worktree)}/sweeps", patterns)


def docs(group: dict, worktree: str, *names: str) -> None:
    exact(group, *(f"{stage(worktree)}/docs/{x}" for x in names))


def source_delta(group: dict, worktree: str) -> None:
    """Preserve behavior prototype as a patch, never promote it to master."""
    base = stage(worktree)
    patch = git("-C", base, "diff", "--binary", "--", "ai/OpexAI")
    if patch:
        group[f"source_overlays/{worktree}.patch"] = (patch + "\n").encode("utf-8")
    untracked = git("-C", base, "ls-files", "--others", "--exclude-standard", "--", "ai/OpexAI")
    for path in untracked.splitlines():
        if path and path.endswith(".nut"):
            exact(group, f"{base}/{path}")
    group[f"source_overlays/{worktree}.base.txt"] = (
        git("-C", base, "rev-parse", "HEAD") + "\n").encode("ascii")


def tree(group: dict, directory: str) -> None:
    folder = ROOT / directory
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            group[path.relative_to(ROOT).as_posix()] = path.read_bytes()


def frozen_bundle(group: dict, worktree: str, campaign_name: str) -> None:
    """Retain exact source bundle used by a benchmark; no rebuild or Docker."""
    tree(group, f"{stage(worktree)}/results/{campaign_name}_bundle")


def p4_guard() -> dict:
    g: dict[str, bytes] = {}
    s = "scores_p4_guard_stage_20261013"
    docs(g, s, "scores_p4_guard_air_uplift_20261013.md")
    scripts(g, s, "verify_p4_guard_gate_20261013.py", "test_verify_p4_guard_gate_20261013.py",
            "test_scores_p4_air_uplift_guard_20261013.py", "test_scores_p4_vyear_20261013.py")
    campaign(g, s, "scores_p4_guard_vs_history_dev5x5_20261013",
             "scores_p4_guard_gateA40x5_20261013", "scores_p4_guard_clean_dev5x5_20261013")
    extra_result(g, s, "scores_p4_guard_gate_independent_receipt_20261013.json",
                 "scores_p4_guard_gateA40x5_effect_20261013.json")
    frozen_bundle(g, s, "scores_p4_guard_gateA40x5_20261013")
    source_delta(g, s)
    exact(g, "docs/scores_p2_p4_qualification_independante_20261013.md")
    return g


def c77_fork() -> dict:
    g: dict[str, bytes] = {}
    s = "scores_c77_fork_runtime_stage_20261013"
    docs(g, s, "c77_same_save_fork_verdict_20261014.md")
    scripts(g, s, "c77_savefork_host_20261013.py", "test_c77_savefork_host_20261013.py",
            "analyse_c77_same_save_marginal_20261013.py", "compare_c77_fork_aa_saves_20261013.py",
            "extend_c77_same_save_fork_20261014.py")
    for run in ("c77_historical_exact_source_dedicated2m_20261014",
                "c77_seed314159_dedicated4m_20261014",
                "c77_seed161803_dedicated12m_20261014"):
        tree(g, f"{stage(s)}/results/{run}")
    matching(g, f"{stage(s)}/results", (
        "c77_historical_exact_source_dedicated2m_AA_20261014.json",
        "c77_seed314159_dedicated4m_AA_20261014.json",
        "c77_seed314159_dedicated4m_analysis_20261014.json",
        "c77_live_rail_rail_seed161803_*analysis_20261014.json",
    ))
    source_delta(g, s)
    for other, document in (("scores_c77_replay_stage_20261013", "scores_c77_replay_20261013.md"),
                            ("scores_c77_rank2_policy_stage_20261014", "c77_rank2_policy_experiment_20261014.md")):
        docs(g, other, document)
        scripts(g, other, "test_c77_replay_20261013.py")
        source_delta(g, other)
    matching(g, f"{stage('scores_c77_rank2_policy_stage_20261014')}/results", (
        "*rail*rail*5x5*.json", "*rail*rail*5x5*.jsonl", "*rail*rail*5x5*.manifest.json",
    ))
    return g


def p2_calibration() -> dict:
    g: dict[str, bytes] = {}
    s = "scores_p2_stage_20261013"
    docs(g, s, "scores_p2_stage_20261013.md")
    scripts(g, s, "analyse_score_cold_p2.py", "analyse_score_cold_execution_p2.py",
            "test_analyse_score_cold_execution_p2.py", "test_score_cold_p2_shadow.py")
    campaign(g, s, "scores_p2_dev5x5_20261013")
    extra_result(g, s, "scores_p2_dev5x5_20261013_execution_analysis.json",
                 "scores_p2_dev5x5_20261013_rank_analysis.json")
    frozen_bundle(g, s, "scores_p2_dev5x5_20261013")
    source_delta(g, s)
    recal = "scores_p2_recal_stage_20261013"
    docs(g, recal, "scores_p2_full_population_audit_20261013.md")
    scripts(g, recal, "analyse_p2_recal_oos_20261013.py", "test_analyse_p2_recal_oos_20261013.py")
    matching(g, f"{stage(recal)}/docs", ("*p2*recal*20261013.json",))
    source_delta(g, recal)
    p3 = "scores_p3_stage_20261013"
    matching(g, f"{stage(p3)}/results", ("*p3*40x5*.json", "*p3*40x5*.jsonl",
                                             "*p3*40x5*.manifest.json"))
    exact(g, "docs/scores_estimateurs_resultats_20261013.md")
    return g


def p2_p4_closure() -> dict:
    g: dict[str, bytes] = {}
    exact(g, "docs/p2_p4_bilan_final_et_suspension_20261014.md",
          "docs/scores_p2_p4_experimentation_complementaire_20261013.md")
    for s, doc in (
        ("scores_p2_p4_causal_closure_stage_20261014", "p2_p4_causal_closure_and_open_mechanisms_20261014.md"),
        ("scores_p2_p4_empty_pool_causality_stage_20261014", "p2_p4_empty_pool_and_recovered_fork_20261014.md"),
        ("scores_p2_p4_fleet_opportunity_stage_20261014", "p2_p4_fleet_air_displacement_20261014.md"),
        ("scores_p2_p4_net_revenue_stage_20261014", "p2_p4_net_revenue_experiment_20261014.md"),
        ("scores_p2_p4_signed_hub_stage_20261014", "p2_p4_signed_hub_externality_20261014.md"),
        ("scores_p2_p4_integrated_probe_stage_20261013", "scores_p2_p4_experimental_verdict_20261013.md"),
    ):
        docs(g, s, doc)
        source_delta(g, s)
    for s, patterns in (
        ("scores_p2_p4_causal_closure_stage_20261014", ("qualify_p2_p4_evidence_20261014.py", "test_qualify_p2_p4_evidence_20261014.py")),
        ("scores_p2_p4_empty_pool_causality_stage_20261014", ("analyze_h3_empty_pool_20261014.py", "test_analyze_h3_empty_pool_20261014.py")),
        ("scores_p2_p4_fleet_opportunity_stage_20261014", ("test_p2_fleet_displacement_20261014.py",)),
        ("scores_p2_p4_net_revenue_stage_20261014", ("test_p2_net_revenue_20261014.py", "compare_p2_net_fork_aa_20261014.py")),
        ("scores_p2_p4_signed_hub_stage_20261014", ("test_c121_hub_signed_20261014.py",)),
        ("scores_p4_air_crash_only_stage_20261013", ("analyse_p4_crash_only_effect_20261013.py", "consolide_p4_crash_only_pilot_20261013.py")),
    ):
        scripts(g, s, *patterns)
    extra_result(g, "scores_p2_p4_causal_closure_stage_20261014", "p2_p4_causal_closure_20261014.json")
    extra_result(g, "scores_p2_p4_empty_pool_causality_stage_20261014", "h3_empty_pool_fork_lineage_20261014.json")
    for s, names in (
        ("scores_p2_p4_fleet_opportunity_stage_20261014", ("p2_p4_fleet_displace_exposure3x5_20261014",)),
        ("scores_p2_p4_net_revenue_stage_20261014", ("p2_p4_net_revenue_parity5x5_20261014", "p2_p4_net_revenue_precheck2x2_20261014")),
        ("scores_p2_p4_signed_hub_stage_20261014", ("p2_p4_signed_hub_dev5x5_20261014",)),
    ):
        campaign(g, s, *names)
        frozen_bundle(g, s, names[0])
    matching(g, f"{stage('scores_p4_air_crash_only_stage_20261013')}/results",
             ("scores_p4_air_crash_only_pilot5x5_consolidated_20261013.json",))
    return g


def p0_topk() -> dict:
    g: dict[str, bytes] = {}
    s = "p0_topk_binary_stage_20261012"
    docs(g, s, "p0_topk_binary_stage_20261012.md")
    scripts(g, s, "*p0_topk*.py")
    campaign(g, s, "p0_topk_binary_b20x10_20261012",
             "p0_topk_binary_noprobe_b20x10_20261012",
             "p0_topk_check5_5y_20261012")
    frozen_bundle(g, s, "p0_topk_binary_b20x10_20261012")
    matching(g, f"{stage(s)}/results", ("p0_topk_binary_*global*.json",
                                           "p0_topk_binary_*construction.json",
                                           "p0_topk_check5_5y_20261012_parity.json",
                                           "p0_topk_binary_save_load_20261012.json"))
    source_delta(g, s)
    exact(g, "docs/v154_select_bisect_20261012.md") if (ROOT / "docs/v154_select_bisect_20261012.md").is_file() else None
    return g


def p0_diagnostics() -> dict:
    g: dict[str, bytes] = {}
    experiments = (
        ("p0_projects_abandon_stage_20261012", ("p0_abandon_skip_b20x10_20261012",)),
        ("p0_visible_competition_stage_20261012", ("p0_visible_competition_a40x3_20261012",)),
        ("p0_air_veto_shadow_stage_20261012", ("p0_air_live_veto_shadow_diag3x5_20261012",)),
        ("p0_opcode_tail_stage_20261012", ("p0_tail_shadow_ab5x5_20261012",)),
        ("p0_rail_block_exposure_stage_20261012", ("p0_rail_block_exposure_diag3x5_20261012",)),
        ("p0_air_throughput_diag_stage_20261012", ("p0_air_c117_diag3x5_20261012",)),
        ("p0_projects_causal_stage_20261012", ("p0_projects_conversion_diag3x5_20261012_r2",)),
        ("p0_road_cargo_shadow_stage_20261012", ()),
    )
    for s, names in experiments:
        matching(g, f"{stage(s)}/docs", ("p0_*.md",))
        scripts(g, s, "*p0*.py")
        for name in names:
            matching(g, f"{stage(s)}/results", (name + ".json", name + ".jsonl",
                                                     name + ".manifest.json", name + "_analysis.json"))
        if s in ("p0_projects_abandon_stage_20261012", "p0_visible_competition_stage_20261012"):
            frozen_bundle(g, s, names[0])
        source_delta(g, s)
    matching(g, f"{stage('p0_road_cargo_shadow_stage_20261012')}/results", (
        "p0_road_cargo_shadow_diag3x5_20261012.jsonl",
        "p0_road_cargo_shadow_diag3x5_20261012.manifest.json"))
    exact(g, "docs/v159_c117_lean_20261012.md") if (ROOT / "docs/v159_c117_lean_20261012.md").is_file() else None
    return g


GROUPS = {
    "p4_guard_independent": p4_guard,
    "c77_same_save": c77_fork,
    "p2_cold_calibration": p2_calibration,
    "p2_p4_hypotheses_closure": p2_p4_closure,
    "p0_topk_equivalence": p0_topk,
    "p0_negative_diagnostics": p0_diagnostics,
}


def write_zip(name: str, entries: dict[str, bytes]) -> dict:
    if not entries:
        raise RuntimeError(f"Empty archive: {name}")
    # A previous Windows process can temporarily hold an already completed
    # archive open; use a distinct final name for the large P0 diagnostic lot.
    output = DEST / ("p0_negative_diagnostics_frozen.zip" if name == "p0_negative_diagnostics"
                     else f"{name}.zip")
    inventory = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as bundle:
        for path, data in sorted(entries.items()):
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError(f"Unsafe archive path: {path}")
            info = zipfile.ZipInfo(path, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=6)
            inventory.append({"path": path, "bytes": len(data), "sha256": sha(data)})
    return {"file": output.name, "members": inventory, "archive_bytes": output.stat().st_size,
            "archive_sha256": sha(output.read_bytes())}


def main() -> None:
    if not (ROOT / "ai/OpexAI").is_dir():
        raise RuntimeError("Repository structure not found")
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "date": "2026-10-18", "master_snapshot_commit": git("rev-parse", "master"),
                "scope": "historical research only; no promotion to OpexAI default",
                "archives": {}}
    for name, collector in GROUPS.items():
        print("Packing", name, flush=True)
        files = collector()
        manifest["archives"][name] = write_zip(name, files)
        print("  ", len(files), "members,",
              round(manifest["archives"][name]["archive_bytes"] / 1048576, 2), "MiB", flush=True)
    (DEST / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    print("Saved", DEST / "MANIFEST.json")


if __name__ == "__main__":
    main()
