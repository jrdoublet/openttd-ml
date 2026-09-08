"""Trace C39.0 : observer le bus d'invalidation sans en mesurer la valeur.

La sonde C39 est volontairement passive, mais son propre AILog ajoute du travail d'observation.
Ce diagnostic ne compare donc jamais valeur ou profit : il repond seulement
aux questions architecturales suivantes : quelles notifications arrivent vraiment, quels IDs et
couches sont coalesces, et quel rebuild mensuel les absorbe.

OpenTTDLab ne capture AILog que si OpenTTD est lance avec `-d script=4`. Son API n'expose pas cette
option ; sous Linux, le Pool herite du patch de `subprocess.check_output` pose avant l'experience.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
FAIL_RE = re.compile(r"Your script made an error|The script died unexpectedly")

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    """Ajoute le niveau Info uniquement au processus de partie, pas aux screenshots."""
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def _fields(rest):
    return {key: value for token in rest.split() if "=" in token
            for key, _, value in (token.partition("="),)}


def parse_trace(output):
    """Extrait les seuls enregistrements C39, plus les erreurs explicites du script."""
    events, errors = [], []
    for line in (output or "").splitlines():
        if FAIL_RE.search(line):
            errors.append(line.strip()[:240])
        match = OPEX_RE.search(line)
        if not match:
            continue
        year, month, day, kind, rest = match.groups()
        if kind not in ("C39_DIRTY", "C39_REFRESH", "C39_DECISION_DELTA", "C39_ENGINE_DELTA",
                        "C41_REVISION", "C41_ACK", "C41_WATER_REFRESH", "C41_ROAD_REFRESH", "C41_ROAD_CANDIDATE_PROFILE", "C41_ROAD_FREIGHT_PROFILE", "C41_ROAD_FREIGHT_TOWN_PROFILE", "C41_WATER_PLANS", "C41_WATER_PLAN_PROFILE", "C41_SLACK_LEDGER", "C41_STALENESS_ACK", "C41_OPPORTUNITY_LEDGER", "C41_ADMISSION_LEDGER", "C41_VEHICLE_LOST", "C41_RAIL_LOST", "C41_RAIL_LOST_TOPOLOGY", "C41_RAIL_LOST_PHYSICAL", "C41_RAIL_SIGNAL_ARM", "C41_RAIL_SIGNAL_REPAIR", "C41_RAIL_LOST_CONNECTIVITY",
                        "C39_AIR_ENGINE_REASON"):
            continue
        events.append({
            "date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
            "kind": kind,
            "fields": _fields(rest),
            "raw": match.group(0),
        })
    return events, errors


def keep(row):
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        # Le journal est identique pour toutes les autosauvegardes d'une partie ; le parent le
        # dédupliquera par graine après la fin de l'expérience.
        "output": row.get("output") or "",
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--c41-revision-probe", action="store_true",
                        help="active le registre passif C41.0 dans la trace")
    parser.add_argument("--c41-water-refresh", action="store_true",
                        help="active la micro-tache experimentale C41.1 (implique le registre C41.0)")
    parser.add_argument("--c41-water-precheck", action="store_true",
                        help="active le prefiltre experimental C41.2 (implique C41.1)")
    parser.add_argument("--c41-water-candidate-probe", action="store_true",
                        help="active la sonde C41.3 de plans eau (implique C41.1/C41.2)")
    parser.add_argument("--c41-water-plans-profile", action="store_true",
                        help="active C41.3a : ventilation sites/paires/BFS/economie et metriques de fraicheur")
    parser.add_argument("--c41-water-site-profile", action="store_true",
                        help="active C41.3b : sous-ventilation filtre cotier vs AITestMode dock")
    parser.add_argument("--c41-slack-ledger", action="store_true",
                        help="active C41.11 : ledger annuel passif du slack par categorie de scheduler")
    parser.add_argument("--c41-staleness-ledger", action="store_true",
                        help="active C41.12 : age passif de chaque couche au moment de son acquittement")
    parser.add_argument("--c41-opportunity-ledger", action="store_true",
                        help="active C41.13 : slack observe pendant que chaque couche reste stale")
    parser.add_argument("--c41-admission-ledger", action="store_true",
                        help="active C41.14 : admissibilite passive de la micro-tache catalogue ciblee")
    parser.add_argument("--c41-road-refresh", action="store_true",
                        help="active C41.15 : refresh cible du catalogue route apres EngineAvailable route")
    parser.add_argument("--c41-road-candidate-profile", action="store_true",
                        help="active C41.16 : ventilation passive pax/fret/feeder/TopK des candidats route")
    parser.add_argument("--c41-road-freight-profile", action="store_true",
                        help="active C41.17 : ventilation passive preparation/fret industrie/fret ville")
    parser.add_argument("--c41-road-freight-served-index", action="store_true",
                        help="active C41.18 : index local des origines rail/route servies du fret")
    parser.add_argument("--c41-road-freight-town-profile", action="store_true",
                        help="active C41.19 : detail acceptation/economie des puits urbains fret")
    parser.add_argument("--road-pax-build", action="store_true",
                        help="active les candidats passagers route pour un diagnostic de cout")
    parser.add_argument("--c41-vehicle-lost-probe", action="store_true",
                        help="active la sonde C41.4 d'attribution passive VehicleLost")
    parser.add_argument("--c41-rail-lost-probe", action="store_true",
                        help="active la sonde C41.5 des faits ordre/position/depot rail")
    parser.add_argument("--c41-rail-lost-topology-probe", action="store_true",
                        help="active la sonde C41.6 de topologie persistee des Lost rail")
    parser.add_argument("--c41-rail-lost-physical-probe", action="store_true",
                        help="active la sonde C41.7 des approches et fronts de depot rail")
    parser.add_argument("--c41-rail-lost-signal-repair", action="store_true",
                        help="active la reparation PBS experimentale C41.8")
    parser.add_argument("--c41-rail-lost-connectivity-probe", action="store_true",
                        help="active la sonde C41.9 de connectivite locale rail")
    parser.add_argument("--c39-air-reason-probe", action="store_true",
                        help="active la sonde C39.4 des motifs de non-selection air")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c39_decision_delta_6y_5seeds.json")
    args = parser.parse_args()
    if args.years <= 0 or args.workers <= 0:
        parser.error("--years et --workers doivent etre strictement positifs")

    enable_savegame_cleanup()
    settings = [("c39_invalidation_probe", 1), ("c39_decision_delta_probe", 1),
                ("c39_air_reason_probe", int(args.c39_air_reason_probe)), ("decision_log", 0)]
    if (args.c41_vehicle_lost_probe or args.c41_rail_lost_probe or args.c41_rail_lost_topology_probe
            or args.c41_rail_lost_physical_probe or args.c41_rail_lost_signal_repair
            or args.c41_rail_lost_connectivity_probe):
        settings.append(("c41_vehicle_lost_probe", 1))
    if (args.c41_rail_lost_probe or args.c41_rail_lost_topology_probe
            or args.c41_rail_lost_physical_probe or args.c41_rail_lost_signal_repair
            or args.c41_rail_lost_connectivity_probe):
        settings.append(("c41_rail_lost_probe", 1))
    if args.c41_rail_lost_topology_probe:
        settings.append(("c41_rail_lost_topology_probe", 1))
    if args.c41_rail_lost_physical_probe:
        settings.append(("c41_rail_lost_physical_probe", 1))
    if args.c41_rail_lost_signal_repair:
        settings.append(("c41_rail_lost_signal_repair", 1))
    if args.c41_rail_lost_connectivity_probe:
        settings.append(("c41_rail_lost_connectivity_probe", 1))
    if (args.c41_revision_probe or args.c41_water_refresh or args.c41_water_precheck
            or args.c41_water_candidate_probe or args.c41_water_plans_profile or args.c41_water_site_profile
            or args.c41_staleness_ledger or args.c41_opportunity_ledger or args.c41_admission_ledger
            or args.c41_road_refresh):
        settings.append(("c41_revision_probe", 1))
    if args.c41_water_refresh or args.c41_water_precheck or args.c41_water_candidate_probe or args.c41_water_plans_profile or args.c41_water_site_profile:
        settings.append(("c41_water_refresh", 1))
    if args.c41_water_precheck or args.c41_water_candidate_probe or args.c41_water_plans_profile or args.c41_water_site_profile:
        settings.append(("c41_water_precheck", 1))
    if args.c41_water_candidate_probe or args.c41_water_plans_profile or args.c41_water_site_profile:
        settings.append(("c41_water_candidate_probe", 1))
    if args.c41_water_plans_profile or args.c41_water_site_profile:
        settings.append(("c41_water_plans_profile", 1))
    if args.c41_water_site_profile:
        settings.append(("c41_water_site_profile", 1))
    if args.c41_slack_ledger:
        settings.append(("c41_slack_ledger", 1))
    if args.c41_staleness_ledger:
        settings.append(("c41_staleness_ledger", 1))
    if args.c41_opportunity_ledger:
        settings.append(("c41_opportunity_ledger", 1))
    if args.c41_admission_ledger:
        settings.append(("c41_admission_ledger", 1))
    if args.c41_road_refresh:
        settings.append(("c41_road_refresh", 1))
    if args.c41_road_candidate_profile:
        settings.append(("c41_road_candidate_profile", 1))
    if args.c41_road_freight_profile:
        settings.append(("c41_road_freight_profile", 1))
    if args.c41_road_freight_served_index:
        settings.append(("c41_road_freight_served_index", 1))
    if args.c41_road_freight_town_profile:
        settings.append(("c41_road_freight_town_profile", 1))
    if args.road_pax_build:
        settings.append(("road_pax_build", 1))
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", tuple(settings))
    experiments = [
        {"seed": seed, "days": 365 * args.years, "openttd_config": make_cfg(1970), "ais": (ai,)}
        for seed in args.seeds
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers, result_processor=keep, experiments=experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    logs = {}
    for row in rows:
        if row["seed"] not in logs and row["output"]:
            logs[row["seed"]] = row["output"]
    per_seed, all_events, all_errors = {}, [], []
    for seed in args.seeds:
        trace, errors = parse_trace(logs.get(seed, ""))
        counts = Counter(event["kind"] for event in trace)
        dirty_reasons = Counter(event["fields"].get("reason", "?") for event in trace
                               if event["kind"] == "C39_DIRTY")
        refreshes_with_events = sum(
            1 for event in trace
            if event["kind"] == "C39_REFRESH" and event["fields"].get("events", "0") != "0"
        )
        decision_deltas = [event for event in trace if event["kind"] == "C39_DECISION_DELTA"]
        engine_deltas = [event for event in trace if event["kind"] == "C39_ENGINE_DELTA"]
        c41_revisions = [event for event in trace if event["kind"] == "C41_REVISION"]
        c41_acks = [event for event in trace if event["kind"] == "C41_ACK"]
        c41_water_refreshes = [event for event in trace if event["kind"] == "C41_WATER_REFRESH"]
        c41_road_refreshes = [event for event in trace if event["kind"] == "C41_ROAD_REFRESH"]
        c41_road_candidate_profiles = [event for event in trace if event["kind"] == "C41_ROAD_CANDIDATE_PROFILE"]
        c41_road_freight_profiles = [event for event in trace if event["kind"] == "C41_ROAD_FREIGHT_PROFILE"]
        c41_road_freight_town_profiles = [event for event in trace if event["kind"] == "C41_ROAD_FREIGHT_TOWN_PROFILE"]
        c41_water_plan_probes = [event for event in trace if event["kind"] == "C41_WATER_PLANS"]
        c41_water_plan_profiles = [event for event in trace if event["kind"] == "C41_WATER_PLAN_PROFILE"]
        c41_slack_ledger = [event for event in trace if event["kind"] == "C41_SLACK_LEDGER"]
        c41_staleness_acks = [event for event in trace if event["kind"] == "C41_STALENESS_ACK"]
        c41_opportunity_ledger = [event for event in trace if event["kind"] == "C41_OPPORTUNITY_LEDGER"]
        c41_admission_ledger = [event for event in trace if event["kind"] == "C41_ADMISSION_LEDGER"]
        c41_vehicle_lost = [event for event in trace if event["kind"] == "C41_VEHICLE_LOST"]
        c41_rail_lost = [event for event in trace if event["kind"] == "C41_RAIL_LOST"]
        c41_rail_lost_topology = [event for event in trace if event["kind"] == "C41_RAIL_LOST_TOPOLOGY"]
        c41_rail_lost_physical = [event for event in trace if event["kind"] == "C41_RAIL_LOST_PHYSICAL"]
        c41_rail_signal_arms = [event for event in trace if event["kind"] == "C41_RAIL_SIGNAL_ARM"]
        c41_rail_signal_repairs = [event for event in trace if event["kind"] == "C41_RAIL_SIGNAL_REPAIR"]
        c41_rail_connectivity = [event for event in trace if event["kind"] == "C41_RAIL_LOST_CONNECTIVITY"]
        air_reasons = [event for event in trace if event["kind"] == "C39_AIR_ENGINE_REASON"]
        per_seed[str(seed)] = {
            "c39_dirty": counts["C39_DIRTY"],
            "c39_refresh": counts["C39_REFRESH"],
            "refreshes_with_events": refreshes_with_events,
            "decision_deltas": len(decision_deltas),
            "top_changed_after_event": sum(
                event["fields"].get("top_changed") == "1" for event in decision_deltas
            ),
            "engine_deltas": len(engine_deltas),
            "engines_retained": sum(
                event["fields"].get("retained") == "1" for event in engine_deltas
            ),
            "c41_revisions": len(c41_revisions),
            "c41_acknowledgements": len(c41_acks),
            "c41_water_refreshes": len(c41_water_refreshes),
            "c41_water_ops": sum(int(event["fields"].get("ops", 0)) for event in c41_water_refreshes),
            "c41_road_refreshes": len(c41_road_refreshes),
            "c41_road_ops": sum(int(event["fields"].get("ops", 0)) for event in c41_road_refreshes),
            "c41_road_staleness_age_days": [int(event["fields"].get("staleness_age_days", -1))
                                             for event in c41_road_refreshes],
            "c41_road_candidate_profiles": [event["fields"] for event in c41_road_candidate_profiles],
            "c41_road_freight_profiles": [event["fields"] for event in c41_road_freight_profiles],
            "c41_road_freight_town_profiles": [event["fields"] for event in c41_road_freight_town_profiles],
            "c41_water_plan_probes": len(c41_water_plan_probes),
            "c41_water_plan_ops": sum(int(event["fields"].get("ops", 0)) for event in c41_water_plan_probes),
            "c41_water_plans": sum(int(event["fields"].get("plans", 0)) for event in c41_water_plan_probes),
            "c41_water_plan_profiles": len(c41_water_plan_profiles),
            "c41_water_staleness_age_days": [int(event["fields"].get("staleness_age_days", -1))
                                              for event in c41_water_refreshes],
            "c41_water_slack_ops_used": sum(int(event["fields"].get("slack_ops_used", 0))
                                              for event in c41_water_refreshes),
            "c41_water_profile_slack_ops_used": sum(int(event["fields"].get("slack_ops_used", 0))
                                                      for event in c41_water_plan_profiles),
            "c41_water_profile_ops": {
                key: sum(int(event["fields"].get(key, 0)) for event in c41_water_plan_profiles)
                for key in ("town_sort_ops", "site_ops", "site_scan_filter_ops", "dock_test_ops",
                            "pair_total_ops", "pair_filter_rank_ops", "bfs_ops", "economics_ops")
            },
            "c41_slack_ledger": [event["fields"] for event in c41_slack_ledger],
            "c41_staleness_acknowledgements": [event["fields"] for event in c41_staleness_acks],
            "c41_opportunity_ledger": [event["fields"] for event in c41_opportunity_ledger],
            "c41_admission_ledger": [event["fields"] for event in c41_admission_ledger],
            "c41_vehicle_lost": len(c41_vehicle_lost),
            "c41_vehicle_lost_mapped": sum(event["fields"].get("orphan") == "0" for event in c41_vehicle_lost),
            "c41_vehicle_lost_orphan": sum(event["fields"].get("orphan") == "1" for event in c41_vehicle_lost),
            "c41_vehicle_lost_modes": dict(sorted(Counter(
                event["fields"].get("mode", "?") for event in c41_vehicle_lost).items())),
            "c41_rail_lost": len(c41_rail_lost),
            "c41_rail_lost_unique_line_vehicles": len({
                (event["fields"].get("line", "?"), event["fields"].get("vehicle", "?"))
                for event in c41_rail_lost}),
            "c41_rail_lost_target_line": sum(event["fields"].get("target_line") == "1" for event in c41_rail_lost),
            "c41_rail_lost_depot_valid": sum(event["fields"].get("depot_valid") == "1" for event in c41_rail_lost),
            "c41_rail_lost_states": dict(sorted(Counter(
                event["fields"].get("state", "?") for event in c41_rail_lost).items())),
            "c41_rail_lost_topology": len(c41_rail_lost_topology),
            "c41_rail_lost_double_track": sum(event["fields"].get("double_track") == "1" for event in c41_rail_lost_topology),
            "c41_rail_lost_depot2_valid": sum(event["fields"].get("depot2_valid") == "1" for event in c41_rail_lost_topology),
            "c41_rail_lost_physical": len(c41_rail_lost_physical),
            "c41_rail_lost_physical_missing_approach": sum(
                any(event["fields"].get(key) != "1" for key in ("a_rail", "b_rail", "a2_rail", "b2_rail"))
                for event in c41_rail_lost_physical),
            "c41_rail_signal_arms": len(c41_rail_signal_arms),
            "c41_rail_signal_repairs": len(c41_rail_signal_repairs),
            "c41_rail_signal_pbs_built": sum(
                sum(event["fields"].get(key) == "1" for key in ("a", "b", "a2", "b2"))
                for event in c41_rail_signal_repairs),
            "c41_rail_connectivity": len(c41_rail_connectivity),
            "c41_rail_connectivity_missing_link": sum(
                any(event["fields"].get(key, "-1") == "0" for key in ("a_links", "b_links", "a2_links", "b2_links"))
                for event in c41_rail_connectivity),
            "c39_air_reason_counts": dict(sorted(Counter(
                event["fields"].get("reason", "?") for event in air_reasons).items())),
            "dirty_reasons": dict(sorted(dirty_reasons.items())),
            "errors": errors,
            "trace": trace,
        }
        all_events.extend(trace)
        all_errors.extend({"seed": seed, "line": error} for error in errors)

    kind_counts = Counter(event["kind"] for event in all_events)
    dirty_reasons = Counter(event["fields"].get("reason", "?") for event in all_events
                            if event["kind"] == "C39_DIRTY")
    decision_deltas = [event for event in all_events if event["kind"] == "C39_DECISION_DELTA"]
    engine_deltas = [event for event in all_events if event["kind"] == "C39_ENGINE_DELTA"]
    c41_revisions = [event for event in all_events if event["kind"] == "C41_REVISION"]
    c41_acks = [event for event in all_events if event["kind"] == "C41_ACK"]
    c41_water_refreshes = [event for event in all_events if event["kind"] == "C41_WATER_REFRESH"]
    c41_road_refreshes = [event for event in all_events if event["kind"] == "C41_ROAD_REFRESH"]
    c41_road_candidate_profiles = [event for event in all_events if event["kind"] == "C41_ROAD_CANDIDATE_PROFILE"]
    c41_road_freight_profiles = [event for event in all_events if event["kind"] == "C41_ROAD_FREIGHT_PROFILE"]
    c41_road_freight_town_profiles = [event for event in all_events if event["kind"] == "C41_ROAD_FREIGHT_TOWN_PROFILE"]
    c41_water_plan_probes = [event for event in all_events if event["kind"] == "C41_WATER_PLANS"]
    c41_water_plan_profiles = [event for event in all_events if event["kind"] == "C41_WATER_PLAN_PROFILE"]
    c41_slack_ledger = [event for event in all_events if event["kind"] == "C41_SLACK_LEDGER"]
    c41_staleness_acks = [event for event in all_events if event["kind"] == "C41_STALENESS_ACK"]
    c41_opportunity_ledger = [event for event in all_events if event["kind"] == "C41_OPPORTUNITY_LEDGER"]
    c41_admission_ledger = [event for event in all_events if event["kind"] == "C41_ADMISSION_LEDGER"]
    c41_vehicle_lost = [event for event in all_events if event["kind"] == "C41_VEHICLE_LOST"]
    c41_rail_lost = [event for event in all_events if event["kind"] == "C41_RAIL_LOST"]
    c41_rail_lost_topology = [event for event in all_events if event["kind"] == "C41_RAIL_LOST_TOPOLOGY"]
    c41_rail_lost_physical = [event for event in all_events if event["kind"] == "C41_RAIL_LOST_PHYSICAL"]
    c41_rail_signal_arms = [event for event in all_events if event["kind"] == "C41_RAIL_SIGNAL_ARM"]
    c41_rail_signal_repairs = [event for event in all_events if event["kind"] == "C41_RAIL_SIGNAL_REPAIR"]
    c41_rail_connectivity = [event for event in all_events if event["kind"] == "C41_RAIL_LOST_CONNECTIVITY"]
    air_reasons = [event for event in all_events if event["kind"] == "C39_AIR_ENGINE_REASON"]
    summary = {
        "c39_dirty": kind_counts["C39_DIRTY"],
        "c39_refresh": kind_counts["C39_REFRESH"],
        "refreshes_with_events": sum(
            1 for event in all_events
            if event["kind"] == "C39_REFRESH" and event["fields"].get("events", "0") != "0"
        ),
        "decision_deltas": len(decision_deltas),
        "top_changed_after_event": sum(
            event["fields"].get("top_changed") == "1" for event in decision_deltas
        ),
        "engine_deltas": len(engine_deltas),
        "engines_retained": sum(
            event["fields"].get("retained") == "1" for event in engine_deltas
        ),
        "c41_revisions": len(c41_revisions),
        "c41_acknowledgements": len(c41_acks),
        "c41_water_refreshes": len(c41_water_refreshes),
        "c41_water_ops": sum(int(event["fields"].get("ops", 0)) for event in c41_water_refreshes),
        "c41_road_refreshes": len(c41_road_refreshes),
        "c41_road_ops": sum(int(event["fields"].get("ops", 0)) for event in c41_road_refreshes),
        "c41_road_staleness_age_days": [int(event["fields"].get("staleness_age_days", -1))
                                          for event in c41_road_refreshes],
        "c41_road_candidate_profiles": [event["fields"] for event in c41_road_candidate_profiles],
        "c41_road_freight_profiles": [event["fields"] for event in c41_road_freight_profiles],
        "c41_road_freight_town_profiles": [event["fields"] for event in c41_road_freight_town_profiles],
        "c41_water_plan_probes": len(c41_water_plan_probes),
        "c41_water_plan_ops": sum(int(event["fields"].get("ops", 0)) for event in c41_water_plan_probes),
        "c41_water_plans": sum(int(event["fields"].get("plans", 0)) for event in c41_water_plan_probes),
        "c41_water_plan_profiles": len(c41_water_plan_profiles),
        "c41_water_staleness_age_days": [int(event["fields"].get("staleness_age_days", -1))
                                          for event in c41_water_refreshes],
        "c41_water_slack_ops_used": sum(int(event["fields"].get("slack_ops_used", 0))
                                          for event in c41_water_refreshes),
        "c41_water_profile_slack_ops_used": sum(int(event["fields"].get("slack_ops_used", 0))
                                                  for event in c41_water_plan_profiles),
        "c41_water_profile_ops": {
            key: sum(int(event["fields"].get(key, 0)) for event in c41_water_plan_profiles)
            for key in ("town_sort_ops", "site_ops", "site_scan_filter_ops", "dock_test_ops",
                        "pair_total_ops", "pair_filter_rank_ops", "bfs_ops", "economics_ops")
        },
        "c41_slack_ledger": [event["fields"] for event in c41_slack_ledger],
        "c41_staleness_acknowledgements": [event["fields"] for event in c41_staleness_acks],
        "c41_opportunity_ledger": [event["fields"] for event in c41_opportunity_ledger],
        "c41_admission_ledger": [event["fields"] for event in c41_admission_ledger],
        "c41_vehicle_lost": len(c41_vehicle_lost),
        "c41_vehicle_lost_mapped": sum(event["fields"].get("orphan") == "0" for event in c41_vehicle_lost),
        "c41_vehicle_lost_orphan": sum(event["fields"].get("orphan") == "1" for event in c41_vehicle_lost),
        "c41_vehicle_lost_modes": dict(sorted(Counter(
            event["fields"].get("mode", "?") for event in c41_vehicle_lost).items())),
        "c41_rail_lost": len(c41_rail_lost),
        "c41_rail_lost_unique_line_vehicles": sum(
            data["c41_rail_lost_unique_line_vehicles"] for data in per_seed.values()),
        "c41_rail_lost_target_line": sum(event["fields"].get("target_line") == "1" for event in c41_rail_lost),
        "c41_rail_lost_depot_valid": sum(event["fields"].get("depot_valid") == "1" for event in c41_rail_lost),
        "c41_rail_lost_states": dict(sorted(Counter(
            event["fields"].get("state", "?") for event in c41_rail_lost).items())),
        "c41_rail_lost_topology": len(c41_rail_lost_topology),
        "c41_rail_lost_double_track": sum(event["fields"].get("double_track") == "1" for event in c41_rail_lost_topology),
        "c41_rail_lost_depot2_valid": sum(event["fields"].get("depot2_valid") == "1" for event in c41_rail_lost_topology),
        "c41_rail_lost_physical": len(c41_rail_lost_physical),
        "c41_rail_lost_physical_missing_approach": sum(
            any(event["fields"].get(key) != "1" for key in ("a_rail", "b_rail", "a2_rail", "b2_rail"))
            for event in c41_rail_lost_physical),
        "c41_rail_signal_arms": len(c41_rail_signal_arms),
        "c41_rail_signal_repairs": len(c41_rail_signal_repairs),
        "c41_rail_signal_pbs_built": sum(
            sum(event["fields"].get(key) == "1" for key in ("a", "b", "a2", "b2"))
            for event in c41_rail_signal_repairs),
        "c41_rail_connectivity": len(c41_rail_connectivity),
        "c41_rail_connectivity_missing_link": sum(
            any(event["fields"].get(key, "-1") == "0" for key in ("a_links", "b_links", "a2_links", "b2_links"))
            for event in c41_rail_connectivity),
        "c39_air_reason_counts": dict(sorted(Counter(
            event["fields"].get("reason", "?") for event in air_reasons).items())),
        "dirty_reasons": dict(sorted(dirty_reasons.items())),
        "errors": all_errors,
    }
    print("C39 trace:", json.dumps(summary, ensure_ascii=False, sort_keys=True))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "openttd_version": OPENTTD_VERSION,
        "years": args.years,
        "seeds": args.seeds,
        "settings": {"c39_invalidation_probe": 1, "c39_decision_delta_probe": 1,
                     "c39_air_reason_probe": int(args.c39_air_reason_probe),
                     "c41_revision_probe": int(args.c41_revision_probe or args.c41_water_refresh
                                                or args.c41_water_precheck or args.c41_water_candidate_probe
                                                or args.c41_water_plans_profile or args.c41_water_site_profile
                                                or args.c41_staleness_ledger or args.c41_opportunity_ledger
                                                or args.c41_admission_ledger or args.c41_road_refresh),
                     "c41_water_refresh": int(args.c41_water_refresh or args.c41_water_precheck
                                                or args.c41_water_candidate_probe or args.c41_water_plans_profile
                                                or args.c41_water_site_profile),
                     "c41_water_precheck": int(args.c41_water_precheck or args.c41_water_candidate_probe
                                                or args.c41_water_plans_profile or args.c41_water_site_profile),
                     "c41_water_candidate_probe": int(args.c41_water_candidate_probe or args.c41_water_plans_profile
                                                        or args.c41_water_site_profile),
                     "c41_water_plans_profile": int(args.c41_water_plans_profile or args.c41_water_site_profile),
                     "c41_water_site_profile": int(args.c41_water_site_profile),
                     "c41_slack_ledger": int(args.c41_slack_ledger),
                     "c41_staleness_ledger": int(args.c41_staleness_ledger),
                     "c41_opportunity_ledger": int(args.c41_opportunity_ledger),
                     "c41_admission_ledger": int(args.c41_admission_ledger),
                     "c41_road_refresh": int(args.c41_road_refresh),
                     "c41_road_candidate_profile": int(args.c41_road_candidate_profile),
                     "c41_road_freight_profile": int(args.c41_road_freight_profile),
                     "c41_road_freight_served_index": int(args.c41_road_freight_served_index),
                     "c41_road_freight_town_profile": int(args.c41_road_freight_town_profile),
                     "road_pax_build": int(args.road_pax_build),
                     "c41_vehicle_lost_probe": int(args.c41_vehicle_lost_probe or args.c41_rail_lost_probe),
                     "c41_rail_lost_probe": int(args.c41_rail_lost_probe or args.c41_rail_lost_topology_probe or args.c41_rail_lost_physical_probe or args.c41_rail_lost_signal_repair),
                     "c41_rail_lost_topology_probe": int(args.c41_rail_lost_topology_probe),
                     "c41_rail_lost_physical_probe": int(args.c41_rail_lost_physical_probe),
                     "c41_rail_lost_signal_repair": int(args.c41_rail_lost_signal_repair),
                     "c41_rail_lost_connectivity_probe": int(args.c41_rail_lost_connectivity_probe),
                     "decision_log": 0},
        "warning": "Diagnostic trace only: C39 probes write AILog; not a value benchmark.",
        "summary": summary,
        "per_seed": per_seed,
    }, indent=1) + "\n")
    print("ecrit", args.out)


if __name__ == "__main__":
    main()
