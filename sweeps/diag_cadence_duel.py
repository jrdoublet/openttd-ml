"""Diagnostic multi-bras de cadence, jamais un banc d'adoption.

Reutilise les collecteurs/sante du banc officiel et les profits annuels du
diagnostic existant. Conserve logs et checkpoints par partie. Les empreintes
avant/apres detectent une derive des sources ; elles ne remplacent PAS un
bundle execute immuable ni une provenance Git. Aucun defaut IA n'est modifie.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openttdlab
import bench_v2
from bench_1v1_5y_20seeds import extract_company_record
from duel_yearly_ratio import yearly_profits
from game_health import assess_game, enable_engine_failure_capture

ROOT = Path(__file__).resolve().parents[1]
START = 1970
ARMS = {
    "reference": "OpexAI",
    "skip_not_due": "OpexAI[exp_scheduler_skip_not_due=1]",
    "hub_prefilter": "OpexAI[exp_air_hub_pair_prefilter=1]",
}


def enable_script_debug():
    original = openttdlab.subprocess.check_output

    def checked(command, *args, **kwargs):
        command = tuple(command)
        if any(str(part).startswith("-vnull") for part in command):
            command = command[:1] + ("-d", "script=4") + command[1:]
        return original(command, *args, **kwargs)

    openttdlab.subprocess.check_output = checked


def source_hashes(root):
    paths = []
    for directory in ("ai/OpexAI", "ai/AAAHogEx-115", "ai/library", "sweeps"):
        paths.extend(p for p in (root / directory).rglob("*")
                     if p.is_file() and p.suffix in (".nut", ".py"))
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def collect(row):
    """Deux collecteurs officiels, sans perdre les logs en fin d'experience."""
    exp = row["experiment"]
    chunks = row.get("chunks", {})
    output = row.get("output")
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    log_path = Path(exp["log_path"])
    if output is not None:
        log_path.write_text(output, encoding="utf-8")
    records = []
    annual = {}
    for owner, name in ((0, "OpexAI"), (1, "AAAHogEx")):
        rec = extract_company_record(chunks, owner, [name, exp["seed"], 0], row.get("date", ""))
        rec["engine_failure"] = row.get("engine_failure")
        records.append(rec)
        players = chunks.get("PLYR") or {}
        player = players.get(owner) or players.get(str(owner)) or {}
        annual[name] = yearly_profits(player.get("old_economy"), exp["years"])
    result = {"arm": exp["arm"], "seed": exp["seed"], "date": str(row.get("date", "")),
              "records": records, "annual": annual, "log_path": str(log_path)}
    # Un seul worker ecrit la serie d'une partie, pas de fichier partage.
    with Path(exp["checkpoint_path"]).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    return (result,)


def finish_game(rows, years):
    rows = sorted(rows, key=lambda row: row["date"])
    last = rows[-1]
    records = [rec for row in rows for rec in row["records"]]
    log = Path(last["log_path"])
    health = assess_game(records, starting_year=START, years=years,
                         engine_log=log.read_text(encoding="utf-8") if log.exists() else None,
                         engine_log_path=str(log))
    reasons = []
    if not health["game_ok"]:
        reasons.append(health["game_status"])
    # L'annee d'affectation de old_economy exige ce checkpoint exact.
    if last["date"] != f"{START + years}-02-01":
        reasons.append("annual_alignment")
    for name in ("OpexAI", "AAAHogEx"):
        if set(last["annual"][name]) != set(range(years)):
            reasons.append(f"annual_coverage:{name}")
    for rec in last["records"]:
        if not rec["vehs_chunk_valid"] or not rec["stnn_chunk_valid"]:
            reasons.append("physical_decode")
        if rec["profit_year_coverage"] != "complete":
            reasons.append("profit_coverage")
    ratios = {}
    for y in range(years):
        o = last["annual"]["OpexAI"].get(y)
        a = last["annual"]["AAAHogEx"].get(y)
        ratios[START + y] = 100 * o / a if o is not None and a is not None and a > 0 else None
    if any(value is None for value in ratios.values()):
        reasons.append("ratio_undefined")
    return {"arm": last["arm"], "seed": last["seed"], "date": last["date"],
            "valid": not reasons, "reasons": reasons, "health": health,
            "ratio_pct": ratios, "annual": last["annual"], "final": last["records"],
            "log_path": str(log)}


def compare(games, arms, seeds, years):
    """Aucune moyenne sur sous-ensemble favorable en cas d'echec ou de trou."""
    indexed = {(g["arm"], g["seed"]): g for g in games}
    expected = {(a, s) for a in arms for s in seeds}
    valid = (len(indexed) == len(games) and set(indexed) == expected
             and all(g["valid"] for g in games))
    if not valid:
        return {"complete": False, "annual": {}, "paired_final": {}}
    annual = {}
    for a in arms:
        annual[a] = {START + y: statistics.mean(indexed[a, s]["ratio_pct"][START + y]
                                               for s in seeds) for y in range(years)}
    paired = {}
    for a in arms:
        if a == "reference":
            continue
        pairs = []
        for s in seeds:
            ref, var = indexed["reference", s], indexed[a, s]
            op = var["annual"]["OpexAI"][years - 1] - ref["annual"]["OpexAI"][years - 1]
            ap = var["annual"]["AAAHogEx"][years - 1] - ref["annual"]["AAAHogEx"][years - 1]
            pairs.append({"seed": s, "opex_profit_delta": op, "aaa_profit_delta": ap,
                          "gap_delta": op - ap,
                          "ratio_delta_pts": var["ratio_pct"][START + years - 1]
                                             - ref["ratio_pct"][START + years - 1]})
        ref_value = sum(indexed["reference", s]["final"][0]["company_value"] for s in seeds)
        var_value = sum(indexed[a, s]["final"][0]["company_value"] for s in seeds)
        paired[a] = {"per_seed": pairs,
                     **{k: statistics.mean(p[k] for p in pairs) for k in
                        ("opex_profit_delta", "aaa_profit_delta", "gap_delta", "ratio_delta_pts")},
                     "ratio_wins": sum(p["ratio_delta_pts"] > 0 for p in pairs),
                     "value_delta_pct": 100 * (var_value / ref_value - 1) if ref_value > 0 else None}
    return {"complete": True, "annual": annual, "paired_final": paired}


def main(*, arm_specs=None, purpose="diagnostic_only_not_adoption", force_debug=False):
    # Other bounded diagnostics can reuse this collector without copying it or
    # mutating ARMS. Effective settings and purpose remain explicit in plan.json.
    available_arms = dict(ARMS if arm_specs is None else arm_specs)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arms", nargs="+", choices=list(available_arms), default=list(available_arms))
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    p.add_argument("--years", type=int, default=6)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--probe", action="store_true",
                   help="Sondes symetriques de decision/portefeuille, diagnostic d'exposition seulement")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if (not 1 <= args.years <= 6 or not 1 <= args.workers <= 12
            or len(set(args.seeds)) != len(args.seeds)
            or len(set(args.arms)) != len(args.arms) or "reference" not in args.arms):
        p.error("diagnostic: 1..6 ans, 1..12 workers, graines/bras uniques, reference obligatoire")
    artifacts = args.out.with_suffix(".artifacts")
    if args.out.exists() or artifacts.exists():
        p.error("sortie ou artefacts existants : choisir un autre nom")
    hashes = source_hashes(ROOT)
    specs = {a: available_arms[a] for a in args.arms}
    if args.probe:
        for a, spec in specs.items():
            specs[a] = ("OpexAI[decision_log=1,probe_portfolio=1]" if spec == "OpexAI"
                        else spec[:-1] + ",decision_log=1,probe_portfolio=1]")
    built = bench_v2.build_arms(list(specs.values()) + ["AAAHogEx"])
    resolved = bench_v2.resolved_arm_settings(list(specs.values()))
    artifacts.mkdir(parents=True)
    metadata = {"protocol": purpose, "git_sha": None,
                "source_frozen": False, "source_hashes_before": hashes,
                "docker_image_id": os.environ.get("DIAG_DOCKER_IMAGE_ID"),
                "years": args.years, "seeds": args.seeds, "workers": args.workers,
                "arms": specs, "resolved_arms": resolved, "probe": args.probe,
                "script_debug": 4 if args.probe or force_debug else None,
                "criteria": {"primary": "mean_per_seed_annual_ratio_pct",
                             "opex_profit_useful_delta_gbp": 50000,
                             "value_max_loss_pct": 5}}
    (artifacts / "plan.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    days = (date(START + args.years, 1, 1) - date(START, 1, 1)).days + 32
    experiments = [{"arm": a, "seed": s, "years": args.years, "days": days,
                    "openttd_config": bench_v2.make_cfg(START),
                    "ais": (built[specs[a]], built["AAAHogEx"]),
                    "log_path": str(artifacts / f"{a}_{s}.log"),
                    "checkpoint_path": str(artifacts / f"{a}_{s}.jsonl")}
                   for s in args.seeds for a in args.arms]
    bench_v2.enable_savegame_cleanup()
    if args.probe or force_debug:
        enable_script_debug()
    enable_engine_failure_capture()
    rows = list(openttdlab.run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION, opengfx_version=bench_v2.OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=collect,
        ai_libraries=(openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"))))
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["arm"], row["seed"]].append(row)
    games = [finish_game(series, args.years) for _, series in sorted(grouped.items())]
    unchanged = hashes == source_hashes(ROOT)
    report = compare(games, args.arms, args.seeds, args.years)
    if not unchanged:
        report = {"complete": False, "annual": {}, "paired_final": {}}
    payload = {**metadata, "sources_unchanged": unchanged, "games": games, **report}
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"complete": report["complete"], "sources_unchanged": unchanged,
                      "health": [{"arm": g["arm"], "seed": g["seed"], "reasons": g["reasons"]}
                                 for g in games], "annual": report["annual"],
                      "paired_final": report["paired_final"]}, indent=2))
    print(f"JSON: {args.out}")
    if not report["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()