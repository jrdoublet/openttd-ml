#!/usr/bin/env python3
"""Demonstration hors ligne des frontieres modales; aucun appel a OpenTTD.

Les populations sont issues exclusivement du JSON agrege des campagnes PC
SOLO/DUEL commencees en 1970 (40 graines x 10 ans chacun). Les vitesses sont
des SCENARIOS et ne sont pas attribuees aux vehicules reels des 80 parties.
"""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (ROOT / "evidence/review/roi_calibration_predictors_20261021"
            / "bandes_distance_roi_20261021.json")
TICKS_PER_DAY = 74.0
PLANE_DIVISOR = 4.0
LARGE_GROUND_TILES = 2 * (6 + 6)


def days_per_tile_boundary(speed):
    """candidates.nut:153-157 (4096/(74*1.6*v)), jours calendaires/tuile."""
    return 4096.0 / (TICKS_PER_DAY * 1.6 * speed)


def days_per_tile_economy(speed):
    """economy.nut et air_trip.nut (1/(0.036*v)), jours/tuile."""
    return 1.0 / (0.036 * speed)


def maneuver_legacy(plane_speed):
    """candidates.nut:221-238, 26,19 j pour deux AT_LARGE 6x6."""
    taxi = min(150.0, plane_speed) / PLANE_DIVISOR
    return LARGE_GROUND_TILES * days_per_tile_boundary(taxi) + 300.0 / TICKS_PER_DAY


def maneuver_c100(plane_speed):
    """air_trip.nut:15-30 et air_economics_c121.nut:39-61."""
    taxi = min(50.0, plane_speed)
    return (LARGE_GROUND_TILES * (2.0 / 3.0) *
            days_per_tile_boundary(taxi) + 300.0 / TICKS_PER_DAY)


def crossover(speed_rail, speed_air, fixed_days, time_per_tile):
    """Seuil d'egalite T_rail(D)=T_air(D), avant clamp et sans chargement."""
    difference = time_per_tile(speed_rail) - time_per_tile(speed_air)
    if difference <= 0.0:
        return None  # air moins rapide ou egal en croisiere
    return fixed_days / difference


def modal_scenario(rail, aircraft):
    """Separations explicites de la vitesse et de la conversion de jours."""
    historical = aircraft / PLANE_DIVISOR
    return {
        "v_rail_km_h": rail, "v_air_api_km_h": aircraft,
        "v_air_legacy_km_h": historical,
        "fixed_boundary_legacy_days": maneuver_legacy(aircraft),
        "fixed_c100_physical_days": maneuver_c100(aircraft),
        "boundary_legacy": crossover(rail, historical, maneuver_legacy(aircraft), days_per_tile_boundary),
        "boundary_same_speed_3days": crossover(rail, historical, 3.0, days_per_tile_boundary),
        "boundary_c100_direct": crossover(rail, aircraft, maneuver_c100(aircraft), days_per_tile_boundary),
        "economy_legacy_3days": crossover(rail, historical, 3.0, days_per_tile_economy),
        "economy_c121_direct": crossover(rail, aircraft, maneuver_c100(aircraft), days_per_tile_economy),
    }


def road_to_rail(*, fixed_capital_difference, delta_fare_at20, monthly_pax=100.0,
                 track_cost_per_tile=45.0, target_roi=0.40, road_min=7):
    """candidates.nut:265-312, avec delta fare hypothetical £/pax a 20 tuiles.

    On reproduit expressément la DIVISION par 20 de la difference des tarifs
    totaux de reference, qui change fortement le resultat du document 03.
    """
    if delta_fare_at20 <= 0:
        return road_min
    denominator = (12.0 * monthly_pax * (delta_fare_at20 / 20.0)
                   / target_roi - track_cost_per_tile)
    if denominator <= 0 or fixed_capital_difference <= 0:
        return road_min
    return max(road_min, int(fixed_capital_difference / denominator))


def optional_raw_duel_counts(folder, threshold):
    """Verification exacte optionnelle si les LOGS historiques sont montes.

    Ne lit jamais de parties en cours et ne cree aucun fichier intermediaire.
    La distance RAIL_BUILD vient du chantier ; le AIR filtre sur Manhattan
    des centres des villes, recupere depuis PROJECT_CHOSEN.src/dst.
    """
    from analyse_roi_predictors_20261021 import parse

    rows, info = parse(str(folder), "duel")
    rail_all = [r for r in rows if r["mode"] == "rail"]
    rail = [r for r in rail_all if r["cargo"] == "PASS"]
    air = [r for r in rows if r["mode"] == "air"]

    def air_manhattan(r):
        src, dst = int(r["src_tile"]), int(r["dst_tile"])
        return abs(src % 256 - dst % 256) + abs(src // 256 - dst // 256)

    if not air or any(r["src_tile"] is None or r["dst_tile"] is None for r in air):
        raise ValueError("AIR centre-Manhattan manquant dans PROJECT_CHOSEN")
    return {
        "source_folder": str(folder), "mature_rail_passengers": len(rail),
        "mature_rail_all_cargos": len(rail_all), "mature_air_passengers": len(air),
        "rail_dist_lt_threshold": sum(r["dist"] < threshold for r in rail),
        "rail_dist_threshold_to_199": sum(threshold <= r["dist"] < 200 for r in rail),
        "rail_dist_eq200": sum(r["dist"] == 200 for r in rail),
        "rail_dist_gt200": sum(r["dist"] > 200 for r in rail),
        "rail_overlap_at_physical_78": sum(78 <= r["dist"] < 200 for r in rail),
        "air_center_manhattan_eq200": sum(air_manhattan(r) == 200 for r in air),
        "air_center_manhattan_gt200": sum(air_manhattan(r) > 200 for r in air),
        "parse_counts": info,
    }


def demo(source):
    published = json.loads(source.read_text(encoding="utf-8"))
    b = published["bounds"]
    models = {
        "1970_illustrative_rail115_air570": modal_scenario(115.0, 570.0),
        "historical_document_rail128_air320": modal_scenario(128.0, 320.0),
        "slow_rail80_air320": modal_scenario(80.0, 320.0),
        "rail128_air700": modal_scenario(128.0, 700.0),
    }
    # Le JSON de sous-bandes agrège RAIL PASS et fret. Il est donc
    # INTERDIT d'en déduire une exposition au basculement modal PASS.
    # Seuls les journaux bruts donnent cargo=PASS et la distance jointe.
    road = [{"delta_fare_20_tiles_gbp_pax": p,
             "computed_road_max": road_to_rail(fixed_capital_difference=4100.0,
                                                delta_fare_at20=p)}
            for p in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)]
    return {
        "source": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
        "observed": {"bounds": b, "games": published["seen_games"],
                     "epoch_events": published["logged_bounds_events"]},
        "models_hypothetical": models,
        "passenger_reclassification": {
            "requires_cargo_level_raw_logs": True,
            "reason": "published distance histograms pool RAIL freight and PASS; freight is not subject to the PASS modal boundary",
        },
        "hypothetical_road_to_rail_fare_sensitivity": road,
        "notes": [
            "Speed scenarios are hypothetical, not recovered from EPOCH_BOUNDS individual logs.",
            "Old railMax=200 remains fixed; reclassification does not measure newly constructed projects.",
            "Rail AIR boundary uses Manhattan city distance; AIR_BUILD.dist is flight distance.",
            "Rail-air passenger boundary applies only to RAIL cargo PASS, NOT to RAIL freight.",
            "Rail mechanical station dwell is already included in economy.nut at v216f_dwell_pct=100.",
            "AIR loading dwell can be computed offline from engine loading slices but is not in trip model.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--json", action="store_true", help="afficher le detail JSON")
    parser.add_argument("--duel-logs", type=Path, default=None,
                        help="logs historiques DUEL facultatifs pour le compte exact PASS a seuil 64")
    opt = parser.parse_args()
    r = demo(opt.evidence.resolve())
    if opt.duel_logs is not None:
        if not opt.duel_logs.is_dir():
            parser.error("Dossier absent (aucune relance automatique): " + str(opt.duel_logs))
        r["verified_raw_duel_pass_at_64"] = optional_raw_duel_counts(opt.duel_logs, 64)
    if opt.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("Bornes mesurees 1970-1979:", r["observed"])
        print("Frontieres rail->air (tuiles brutes, non bornees) :")
        for name, v in r["models_hypothetical"].items():
            print("  ", name, {k: (round(x, 2) if x is not None else None)
                                  for k, x in v.items() if "boundary" in k or "economy" in k})
        print("Reclassement PASS: impossible à chiffrer avec les seules bandes agrégées (mélangent fret et voyageurs).")
        print("ROUTE->RAIL, differentiel tarif £/pax au trajet de 20 tuiles:",
              r["hypothetical_road_to_rail_fare_sensitivity"])
        if "verified_raw_duel_pass_at_64" in r:
            print("Verification individuelle PASS seuil 64:", r["verified_raw_duel_pass_at_64"])


if __name__ == "__main__":
    main()
